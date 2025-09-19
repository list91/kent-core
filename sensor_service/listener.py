#!/usr/bin/env python3
"""
Listener process for serving sensor data over network
"""

import sys
import os
import socket
import signal
import time
import struct
from threading import Thread, Event
from socketserver import TCPServer, BaseRequestHandler, ThreadingMixIn

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


class SensorDataHandler(BaseRequestHandler):
    """Handler for incoming client connections"""

    def handle(self):
        """Handle a client request"""
        logger = self.server.logger
        client_addr = self.client_address[0]

        try:
            # Set socket timeout
            self.request.settimeout(5.0)

            # Read request (expecting "GET_DATA\n")
            request_data = self.request.recv(1024).decode('utf-8').strip()

            if request_data != config.PROTOCOL_GET_DATA_CMD:
                logger.warning(f"Invalid request from {client_addr}: {request_data[:50]}")
                self.send_error("ERROR: Invalid command")
                return

            logger.debug(f"Received GET_DATA request from {client_addr}")

            # Load current sensor data
            data = utils.load_current_data(config.DATA_DIR)

            if not data:
                logger.warning(f"No data available for {client_addr}")
                self.send_error("ERROR: No data available")
                return

            timestamp, image_data, csv_data = data

            # Check if data is fresh
            if utils.is_data_stale(timestamp, config.MAX_DATA_AGE):
                logger.warning(f"Data is stale for {client_addr}: age={time.time() - timestamp:.1f}s")
                self.send_error("ERROR: No fresh data available")
                return

            # Send response
            self.send_data(timestamp, image_data, csv_data)
            logger.info(f"Sent data to {client_addr}: timestamp={timestamp:.2f}, image={len(image_data)} bytes, csv={len(csv_data)} bytes")

        except socket.timeout:
            logger.warning(f"Timeout handling request from {client_addr}")
        except Exception as e:
            logger.error(f"Error handling request from {client_addr}: {e}")
            try:
                self.send_error(f"ERROR: {str(e)}")
            except:
                pass

    def send_error(self, error_msg):
        """Send error response to client"""
        try:
            response = f"{error_msg}\n"
            self.request.sendall(response.encode('utf-8'))
        except Exception as e:
            self.server.logger.debug(f"Failed to send error: {e}")

    def send_data(self, timestamp, image_data, csv_data):
        """Send sensor data to client"""
        try:
            # Prepare response with protocol format
            response_parts = []

            # Add timestamp
            response_parts.append(f"TIMESTAMP:{timestamp}\n")

            # Add image size and data
            response_parts.append(f"IMAGE_SIZE:{len(image_data)}\n")

            # Send header parts
            header = ''.join(response_parts).encode('utf-8')
            self.request.sendall(header)

            # Send binary image data
            self.request.sendall(image_data)

            # Add CSV size and data
            csv_header = f"CSV_SIZE:{len(csv_data)}\n".encode('utf-8')
            self.request.sendall(csv_header)
            self.request.sendall(csv_data.encode('utf-8'))

            # Add end marker
            end_marker = f"{config.PROTOCOL_END_MARKER}\n".encode('utf-8')
            self.request.sendall(end_marker)

        except Exception as e:
            raise Exception(f"Failed to send data: {e}")


class ThreadedTCPServer(ThreadingMixIn, TCPServer):
    """Threaded TCP server for handling multiple clients"""

    # Allow server to be restarted quickly
    allow_reuse_address = True

    def __init__(self, server_address, handler_class, logger):
        self.logger = logger
        super().__init__(server_address, handler_class)

    def server_bind(self):
        """Override to set socket options before binding"""
        import socket
        # Enable SO_REUSEADDR to allow immediate reuse of the address
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        # Enable SO_REUSEPORT if available (Linux)
        try:
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        except AttributeError:
            # SO_REUSEPORT not available on this platform
            pass
        super().server_bind()


class SensorListener:
    """Main listener process coordinator"""

    def __init__(self):
        # Set up logging
        log_file = os.path.join(config.LOG_DIR, f"{config.LISTENER_PROCESS_NAME}.log")
        utils.ensure_directory(config.LOG_DIR)
        self.logger = utils.setup_logging(config.LISTENER_PROCESS_NAME, log_file, config.LOG_LEVEL)

        self.server = None

    def initialize(self):
        """Initialize the listener"""
        self.logger.info("Initializing sensor listener...")

        # Check if data directory exists
        if not os.path.exists(config.DATA_DIR):
            self.logger.warning(f"Data directory does not exist: {config.DATA_DIR}")
            self.logger.info("Waiting for Reader process to create it...")

        return True

    def run(self):
        """Run the TCP server"""
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                # Kill any existing process using our port
                self._kill_port_process()

                # Create server
                server_address = (config.LISTENER_HOST, config.LISTENER_PORT)
                self.server = ThreadedTCPServer(server_address, SensorDataHandler, self.logger)

                self.logger.info(f"Listening on {config.LISTENER_HOST}:{config.LISTENER_PORT}")

                # Start server in a thread
                server_thread = Thread(target=self.server.serve_forever)
                server_thread.daemon = True
                server_thread.start()

                # Wait for shutdown signal
                while not shutdown_event.is_set():
                    shutdown_event.wait(1)

                self.logger.info("Shutting down server...")
                self.server.shutdown()
                server_thread.join(timeout=5)
                break

            except OSError as e:
                if e.errno == 98 and attempt < max_retries - 1:  # Address already in use
                    self.logger.warning(f"Port {config.LISTENER_PORT} in use, retrying in {retry_delay}s (attempt {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                    continue
                else:
                    self.logger.error(f"Server error: {e}")
                    raise
            except Exception as e:
                self.logger.error(f"Server error: {e}")
                raise

    def _kill_port_process(self):
        """Kill any process using our port"""
        try:
            import subprocess

            # Find process using the port
            result = subprocess.run(
                ['lsof', '-ti', f':{config.LISTENER_PORT}'],
                capture_output=True, text=True, timeout=5
            )

            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                for pid in pids:
                    try:
                        pid = int(pid.strip())
                        self.logger.info(f"Killing process {pid} using port {config.LISTENER_PORT}")
                        subprocess.run(['kill', '-9', str(pid)], timeout=2)
                    except (ValueError, subprocess.TimeoutExpired):
                        pass

                # Wait a moment for the port to be freed
                time.sleep(1)

        except (subprocess.TimeoutExpired, FileNotFoundError):
            # lsof not available or timeout, skip
            pass
        except Exception as e:
            self.logger.debug(f"Error checking port: {e}")
            pass

    def cleanup(self):
        """Clean up resources"""
        self.logger.info("Listener cleanup complete")


def signal_handler(signum, frame):
    """Handle termination signals"""
    print(f"\\nReceived signal {signum}, shutting down gracefully...")
    shutdown_event.set()


def main():
    """Main entry point"""
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

    # Create and initialize listener
    listener = SensorListener()

    if not listener.initialize():
        print("Failed to initialize sensor listener")
        sys.exit(1)

    try:
        # Run server
        listener.run()
    finally:
        # Clean up
        listener.cleanup()


if __name__ == "__main__":
    main()