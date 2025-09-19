#!/usr/bin/env python3
"""
Reader process for continuous sensor data collection
"""

import sys
import os
import time
import signal
import numpy as np
import csv
import subprocess
from datetime import datetime
from threading import Thread, Event
from concurrent.futures import ThreadPoolExecutor

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensor_service import config
from sensor_service import utils

# Global flag for graceful shutdown
shutdown_event = Event()

def set_shutdown_event(event):
    """Set external shutdown event"""
    global shutdown_event
    shutdown_event = event


class LiDARReader:
    """Handler for VL53L5CX LiDAR sensor"""

    def __init__(self, logger):
        self.logger = logger
        self.sensor = None
        self.is_initialized = False
        self.is_ranging_started = False

    def initialize(self):
        """Initialize the LiDAR sensor once at startup"""
        try:
            from vl53l5cx.vl53l5cx import VL53L5CX
            self.logger.info("Initializing VL53L5CX sensor...")

            self.sensor = VL53L5CX()
            self.sensor.init()

            # Set 8x8 mode
            if self.sensor.get_resolution() != config.LIDAR_RESOLUTION:
                self.logger.info(f"Setting LiDAR to 8x8 mode ({config.LIDAR_RESOLUTION} points)")
                self.sensor.set_resolution(config.LIDAR_RESOLUTION)
                self.sensor.set_ranging_frequency_hz(config.LIDAR_FREQUENCY)

            # Start ranging once and keep it running
            self.logger.info("Starting continuous ranging...")
            self.sensor.start_ranging()
            self.is_ranging_started = True

            # Wait for first measurement to stabilize
            time.sleep(0.5)

            self.is_initialized = True
            self.logger.info(f"LiDAR initialized: {self.sensor.get_resolution()} points at {self.sensor.get_ranging_frequency_hz()} Hz")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize LiDAR: {e}")
            self.is_initialized = False
            return False

    def read_data(self):
        """Read distance data from LiDAR sensor (sensor already initialized and ranging)"""
        try:
            if not self.is_initialized or not self.sensor:
                self.logger.warning("LiDAR not initialized, skipping reading")
                return None

            # Simply get the current data (sensor is continuously ranging)
            data = self.sensor.get_ranging_data()
            distances = np.array(data.distance_mm).reshape(8, 8)

            # Process data: filter valid points
            processed_distances = np.copy(distances)
            for row in range(8):
                for col in range(8):
                    d = distances[row, col]
                    if d <= config.LIDAR_MIN_DISTANCE or d >= config.LIDAR_MAX_DISTANCE or d == 0:
                        processed_distances[row, col] = -1

            return processed_distances
        except Exception as e:
            self.logger.error(f"Failed to read LiDAR data: {e}")
            return None

    def cleanup(self):
        """Stop ranging and cleanup sensor resources"""
        try:
            if self.is_ranging_started and self.sensor:
                self.logger.info("Stopping LiDAR ranging...")
                self.sensor.stop_ranging()
                self.is_ranging_started = False
        except Exception as e:
            self.logger.error(f"Error during LiDAR cleanup: {e}")

    def format_csv(self, distances, timestamp):
        """Format distance data as CSV string"""
        try:
            csv_lines = []

            # Add metadata headers
            csv_lines.append('# VL53L5CX 8x8 Distance Measurement')
            csv_lines.append(f'# Timestamp: {datetime.fromtimestamp(timestamp).isoformat()}')
            csv_lines.append(f'# Min valid distance: {config.LIDAR_MIN_DISTANCE} mm')
            csv_lines.append(f'# Max valid distance: {config.LIDAR_MAX_DISTANCE} mm')
            csv_lines.append('# Invalid points marked as: -1')
            csv_lines.append('')

            # Add column headers
            header = ['Row\\Col'] + [f'Col_{i}' for i in range(8)]
            csv_lines.append(','.join(header))

            # Add data rows
            for row in range(8):
                row_data = [f'Row_{row}'] + [f'{distances[row, col]:.0f}' for col in range(8)]
                csv_lines.append(','.join(row_data))

            return '\n'.join(csv_lines)
        except Exception as e:
            self.logger.error(f"Failed to format CSV data: {e}")
            return None


class CameraReader:
    """Handler for camera image capture"""

    def __init__(self, logger):
        self.logger = logger
        self.last_capture_time = 0
        self.min_capture_interval = 0.3  # Minimum 300ms between captures

    def capture_image(self):
        """Capture an image from the camera"""
        process = None
        try:
            # Ensure minimum interval between captures
            current_time = time.time()
            time_since_last = current_time - self.last_capture_time
            if time_since_last < self.min_capture_interval:
                wait_time = self.min_capture_interval - time_since_last
                self.logger.debug(f"Waiting {wait_time:.2f}s before next capture")
                time.sleep(wait_time)

            # Kill any lingering libcamera-still processes
            try:
                subprocess.run(["pkill", "-f", "libcamera-still"], timeout=1)
                time.sleep(0.1)  # Brief pause to ensure process cleanup
            except:
                pass  # Ignore errors from pkill

            # Use libcamera-still to capture image to stdout
            cmd = [
                "libcamera-still",
                "-t", str(config.CAMERA_WAIT_TIME),
                "--width", str(config.CAMERA_WIDTH),
                "--height", str(config.CAMERA_HEIGHT),
                "--nopreview",  # Add nopreview flag to reduce resource usage
                "-o", "-"  # Output to stdout
            ]

            # Use Popen for better process control
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            try:
                stdout, stderr = process.communicate(timeout=3)
                self.last_capture_time = time.time()

                if process.returncode == 0 and stdout:
                    self.logger.debug(f"Captured image: {len(stdout)} bytes")
                    return stdout
                else:
                    self.logger.error(f"Camera capture failed with code {process.returncode}")
                    if stderr:
                        self.logger.debug(f"Camera stderr: {stderr.decode('utf-8', errors='ignore')[:200]}")
                    return None

            except subprocess.TimeoutExpired:
                self.logger.error("Camera capture timeout - killing process")
                process.kill()
                process.wait(timeout=1)
                return None

        except Exception as e:
            self.logger.error(f"Unexpected error during camera capture: {e}")
            if process and process.poll() is None:
                try:
                    process.kill()
                    process.wait(timeout=1)
                except:
                    pass
            return None


class SensorReader:
    """Main reader process coordinator"""

    def __init__(self):
        # Set up logging
        log_file = os.path.join(config.LOG_DIR, f"{config.READER_PROCESS_NAME}.log")
        utils.ensure_directory(config.LOG_DIR)
        self.logger = utils.setup_logging(config.READER_PROCESS_NAME, log_file, config.LOG_LEVEL)

        # Initialize components
        self.lidar_reader = LiDARReader(self.logger)
        self.camera_reader = CameraReader(self.logger)
        self.executor = ThreadPoolExecutor(max_workers=2)

    def initialize(self):
        """Initialize all sensors"""
        self.logger.info("Initializing sensor reader...")

        # Ensure data directory exists
        if not utils.ensure_directory(config.DATA_DIR):
            self.logger.error(f"Failed to create data directory: {config.DATA_DIR}")
            return False

        # Initialize LiDAR (optional - service can work without it)
        lidar_ok = self.lidar_reader.initialize()
        if not lidar_ok:
            self.logger.warning("LiDAR initialization failed, will continue without it")
            self.logger.warning("Only camera data will be available")

        self.logger.info(f"Sensor reader initialized (LiDAR: {'OK' if lidar_ok else 'FAILED'})")
        return True

    def read_sensors_parallel(self):
        """Read both sensors in parallel"""
        try:
            # Submit both read operations
            lidar_future = self.executor.submit(self.lidar_reader.read_data)
            camera_future = self.executor.submit(self.camera_reader.capture_image)

            # Get timestamp
            timestamp = time.time()

            # Wait for results
            lidar_data = lidar_future.result(timeout=5)
            image_data = camera_future.result(timeout=5)

            return timestamp, lidar_data, image_data
        except Exception as e:
            self.logger.error(f"Failed to read sensors: {e}")
            return None, None, None

    def save_data(self, timestamp, lidar_data, image_data):
        """Save sensor data to files atomically"""
        success = True

        # Save timestamp
        timestamp_path = os.path.join(config.DATA_DIR, config.TIMESTAMP_FILE)
        if not utils.save_text_atomic(timestamp_path, str(timestamp)):
            self.logger.error("Failed to save timestamp")
            success = False

        # Save LiDAR data if available, otherwise save empty CSV
        if lidar_data is not None:
            csv_content = self.lidar_reader.format_csv(lidar_data, timestamp)
            if csv_content:
                csv_path = os.path.join(config.DATA_DIR, config.CURRENT_CSV_FILE)
                if not utils.save_text_atomic(csv_path, csv_content):
                    self.logger.error("Failed to save LiDAR data")
                    success = False
            else:
                self.logger.error("Failed to format LiDAR data")
                success = False
        else:
            # Save empty CSV with error message if LiDAR not available
            csv_content = f"# VL53L5CX 8x8 Distance Measurement\n# Timestamp: {datetime.fromtimestamp(timestamp).isoformat()}\n# Error: LiDAR sensor not available\n"
            csv_path = os.path.join(config.DATA_DIR, config.CURRENT_CSV_FILE)
            if not utils.save_text_atomic(csv_path, csv_content):
                self.logger.error("Failed to save empty LiDAR data")
                success = False

        # Save image if available
        if image_data:
            image_path = os.path.join(config.DATA_DIR, config.CURRENT_IMAGE_FILE)
            if not utils.save_file_atomic(image_path, image_data):
                self.logger.error("Failed to save image")
                success = False

        return success

    def run(self):
        """Main loop for continuous sensor reading"""
        self.logger.info("Starting sensor reader main loop")

        iteration = 0
        while not shutdown_event.is_set():
            try:
                iteration += 1
                start_time = time.time()

                # Read sensors in parallel
                timestamp, lidar_data, image_data = self.read_sensors_parallel()

                if timestamp:
                    # Save data atomically
                    if self.save_data(timestamp, lidar_data, image_data):
                        self.logger.debug(f"Iteration {iteration}: Data saved successfully")
                    else:
                        self.logger.warning(f"Iteration {iteration}: Some data failed to save")
                else:
                    self.logger.warning(f"Iteration {iteration}: No sensor data received")

                # Calculate sleep time to maintain interval
                elapsed = time.time() - start_time
                sleep_time = max(0, config.READING_INTERVAL - elapsed)

                if sleep_time > 0:
                    shutdown_event.wait(sleep_time)

            except Exception as e:
                self.logger.error(f"Error in main loop: {e}")
                shutdown_event.wait(config.ERROR_RETRY_INTERVAL)

        self.logger.info("Sensor reader stopped")

    def cleanup(self):
        """Clean up resources"""
        self.logger.info("Cleaning up resources...")

        # Stop LiDAR ranging
        self.lidar_reader.cleanup()

        # Shutdown thread pool
        self.executor.shutdown(wait=True, timeout=5)


def signal_handler(signum, frame):
    """Handle termination signals"""
    print(f"\\nReceived signal {signum}, shutting down gracefully...")
    shutdown_event.set()


def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create and initialize reader
    reader = SensorReader()

    if not reader.initialize():
        print("Failed to initialize sensor reader")
        sys.exit(1)

    try:
        # Run main loop
        reader.run()
    finally:
        # Clean up
        reader.cleanup()


if __name__ == "__main__":
    main()
