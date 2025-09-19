#!/usr/bin/env python3
"""
Main entry point for Kent Core Sensor Service
Runs both Reader and Listener processes in parallel
"""

import sys
import os
import signal
import time
import threading
import logging
from multiprocessing import Process, Event
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sensor_service import config, utils

# Global shutdown event
shutdown_event = Event()

def setup_main_logging():
    """Setup logging for main process"""
    log_file = os.path.join(config.LOG_DIR, "sensor_service_main.log")
    utils.ensure_directory(config.LOG_DIR)
    return utils.setup_logging("sensor_service_main", log_file, config.LOG_LEVEL)

def run_reader_process():
    """Run the reader process"""
    try:
        # Import and run reader
        from sensor_service.reader import SensorReader, set_shutdown_event

        # Set shutdown event for this process
        set_shutdown_event(shutdown_event)

        reader = SensorReader()
        if reader.initialize():
            reader.run()
        reader.cleanup()
    except Exception as e:
        print(f"Reader process error: {e}")
        raise

def run_listener_process():
    """Run the listener process"""
    try:
        # Import and run listener
        from sensor_service.listener import SensorListener, set_shutdown_event

        # Set shutdown event for this process
        set_shutdown_event(shutdown_event)

        listener = SensorListener()
        if listener.initialize():
            listener.run()
        listener.cleanup()
    except Exception as e:
        print(f"Listener process error: {e}")
        raise

def signal_handler(signum, frame):
    """Handle termination signals"""
    logger = logging.getLogger("sensor_service_main")
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    print(f"\nReceived signal {signum}, shutting down gracefully...")

    # Set global shutdown event
    shutdown_event.set()

def wait_for_reader_data(timeout=30):
    """Wait for reader to produce initial data"""
    logger = logging.getLogger("sensor_service_main")
    logger.info("Waiting for Reader to initialize and produce data...")

    start_time = time.time()
    while time.time() - start_time < timeout:
        if shutdown_event.is_set():
            return False

        timestamp_file = os.path.join(config.DATA_DIR, config.TIMESTAMP_FILE)
        if os.path.exists(timestamp_file):
            try:
                with open(timestamp_file, 'r') as f:
                    timestamp = float(f.read().strip())
                # Check if data is recent (within last 10 seconds)
                if time.time() - timestamp < 10:
                    logger.info("Reader is producing data")
                    return True
            except:
                pass

        time.sleep(0.5)

    logger.warning(f"Reader did not produce data within {timeout} seconds")
    return False

def check_network_port(port, timeout=10):
    """Check if network port is available"""
    import socket
    logger = logging.getLogger("sensor_service_main")

    start_time = time.time()
    while time.time() - start_time < timeout:
        if shutdown_event.is_set():
            return False

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex(('localhost', port))
                if result == 0:
                    logger.info(f"Listener is accepting connections on port {port}")
                    return True
        except:
            pass

        time.sleep(0.5)

    logger.warning(f"Port {port} not available within {timeout} seconds")
    return False

def monitor_processes(reader_process, listener_process):
    """Monitor both processes and restart if needed"""
    logger = logging.getLogger("sensor_service_main")

    while not shutdown_event.is_set():
        try:
            # Check if processes are alive
            if not reader_process.is_alive():
                logger.error("Reader process died!")
                if not shutdown_event.is_set():
                    logger.info("Restarting Reader process...")
                    reader_process = Process(target=run_reader_process, name="ReaderProcess")
                    reader_process.start()

            if not listener_process.is_alive():
                logger.error("Listener process died!")
                if not shutdown_event.is_set():
                    logger.info("Restarting Listener process...")
                    listener_process = Process(target=run_listener_process, name="ListenerProcess")
                    listener_process.start()

            # Wait before next check
            shutdown_event.wait(5)

        except Exception as e:
            logger.error(f"Error in process monitoring: {e}")
            shutdown_event.wait(1)

    return reader_process, listener_process

def main():
    """Main function"""
    # Setup logging
    logger = setup_main_logging()

    print("=== Kent Core Sensor Service ===")
    print("Starting Reader and Listener processes...")

    # Setup signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    try:
        # Ensure directories exist
        if not utils.ensure_directory(config.DATA_DIR):
            logger.error(f"Failed to create data directory: {config.DATA_DIR}")
            return 1

        if not utils.ensure_directory(config.LOG_DIR):
            logger.error(f"Failed to create log directory: {config.LOG_DIR}")
            return 1

        logger.info("Starting Kent Core Sensor Service")

        # Start Reader process
        logger.info("Starting Reader process...")
        reader_process = Process(target=run_reader_process, name="ReaderProcess")
        reader_process.start()

        # Wait a bit for reader to initialize
        time.sleep(2)

        # Start Listener process
        logger.info("Starting Listener process...")
        listener_process = Process(target=run_listener_process, name="ListenerProcess")
        listener_process.start()

        # Wait for services to be ready
        print("Waiting for services to initialize...")

        # Wait for reader data (with timeout)
        reader_ready = wait_for_reader_data(timeout=30)
        if not reader_ready and not shutdown_event.is_set():
            logger.warning("Reader initialization may have issues")

        # Wait for listener port (with timeout)
        listener_ready = check_network_port(config.LISTENER_PORT, timeout=10)
        if not listener_ready and not shutdown_event.is_set():
            logger.warning("Listener initialization may have issues")

        if reader_ready and listener_ready:
            print("✓ All services started successfully!")
            logger.info("All services started successfully")
        else:
            print("⚠ Some services may have issues - check logs")
            logger.warning("Some services may have issues")

        print(f"Reader PID: {reader_process.pid}")
        print(f"Listener PID: {listener_process.pid}")
        print(f"Listening on port: {config.LISTENER_PORT}")
        print(f"Data directory: {config.DATA_DIR}")
        print(f"Log directory: {config.LOG_DIR}")
        print("\nPress Ctrl+C to stop...")

        # Start monitoring thread
        monitor_thread = threading.Thread(
            target=monitor_processes,
            args=(reader_process, listener_process),
            daemon=True
        )
        monitor_thread.start()

        # Main loop - wait for shutdown
        while not shutdown_event.is_set():
            shutdown_event.wait(1)

        # Shutdown sequence
        print("\nShutting down...")
        logger.info("Initiating shutdown sequence")

        # Terminate processes gracefully
        if reader_process.is_alive():
            logger.info("Terminating Reader process...")
            reader_process.terminate()

        if listener_process.is_alive():
            logger.info("Terminating Listener process...")
            listener_process.terminate()

        # Wait for graceful shutdown
        shutdown_timeout = 10
        reader_process.join(timeout=shutdown_timeout)
        listener_process.join(timeout=shutdown_timeout)

        # Force kill if necessary
        if reader_process.is_alive():
            logger.warning("Force killing Reader process")
            reader_process.kill()
            reader_process.join()

        if listener_process.is_alive():
            logger.warning("Force killing Listener process")
            listener_process.kill()
            listener_process.join()

        print("✓ All processes stopped")
        logger.info("All processes stopped successfully")
        return 0

    except KeyboardInterrupt:
        print("\nInterrupted by user")
        logger.info("Interrupted by user")
        shutdown_event.set()
        return 0

    except Exception as e:
        print(f"Fatal error: {e}")
        logger.error(f"Fatal error: {e}")
        shutdown_event.set()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)