#!/usr/bin/env python3
"""
Integration tests for sensor service
"""

import unittest
import subprocess
import time
import socket
import tempfile
import os
import signal
import sys


class TestServiceIntegration(unittest.TestCase):
    """Integration tests for the sensor service"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        cls.project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cls.test_host = "localhost"
        cls.test_port = 5556  # Use different port to avoid conflicts

    def setUp(self):
        """Set up each test"""
        self.processes = []

    def tearDown(self):
        """Clean up after each test"""
        # Stop any running processes
        for proc in self.processes:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except:
                try:
                    proc.kill()
                    proc.wait(timeout=2)
                except:
                    pass

    def test_listener_startup_and_connection(self):
        """Test that listener starts and accepts connections"""
        # Skip this test if not on Raspberry Pi or if dependencies missing
        try:
            # Start only the listener process with mock data
            self._create_mock_data()
            listener_proc = self._start_listener()

            # Wait for listener to start
            self.assertTrue(self._wait_for_port(self.test_port, timeout=10))

            # Test connection
            self.assertTrue(self._test_connection())

        except FileNotFoundError:
            self.skipTest("Python environment or dependencies not available")

    def test_full_service_without_sensors(self):
        """Test full service operation without actual sensors"""
        try:
            # Start both processes
            reader_proc = self._start_reader()
            listener_proc = self._start_listener()

            # Wait for services to start
            self.assertTrue(self._wait_for_port(self.test_port, timeout=15))

            # Wait for reader to produce some data
            time.sleep(3)

            # Test data retrieval
            self.assertTrue(self._test_data_retrieval())

        except FileNotFoundError:
            self.skipTest("Python environment or dependencies not available")

    def _create_mock_data(self):
        """Create mock sensor data for testing"""
        data_dir = "/tmp/sensor_data"
        os.makedirs(data_dir, exist_ok=True)

        # Create mock timestamp
        timestamp = str(time.time())
        with open(os.path.join(data_dir, "timestamp.txt"), 'w') as f:
            f.write(timestamp)

        # Create mock image (small JPEG-like data)
        mock_image = b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' ",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x15\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00\xaa\xff\xd9'
        with open(os.path.join(data_dir, "current.jpg"), 'wb') as f:
            f.write(mock_image)

        # Create mock CSV
        mock_csv = """# VL53L5CX 8x8 Distance Measurement
# Timestamp: 2024-01-01T12:00:00
# Min valid distance: 30 mm
# Max valid distance: 4000 mm
# Invalid points marked as: -1

Row\\Col,Col_0,Col_1,Col_2,Col_3,Col_4,Col_5,Col_6,Col_7
Row_0,100,120,110,105,115,125,130,135
Row_1,200,210,205,215,220,225,230,235
Row_2,-1,-1,300,305,310,315,320,325
Row_3,400,405,410,415,420,425,430,435
Row_4,500,505,510,515,520,525,530,535
Row_5,600,605,610,615,620,625,630,635
Row_6,700,705,710,715,720,725,730,735
Row_7,800,805,810,815,820,825,830,835"""
        with open(os.path.join(data_dir, "current.csv"), 'w') as f:
            f.write(mock_csv)

    def _start_reader(self):
        """Start the reader process"""
        python_path = os.path.join(self.project_dir, "venv", "bin", "python3")
        reader_script = os.path.join(self.project_dir, "sensor_service", "reader.py")

        # Set environment variables
        env = os.environ.copy()
        env['PYTHONPATH'] = self.project_dir

        proc = subprocess.Popen(
            [python_path, reader_script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        self.processes.append(proc)
        return proc

    def _start_listener(self):
        """Start the listener process with custom port"""
        python_path = os.path.join(self.project_dir, "venv", "bin", "python3")
        listener_script = os.path.join(self.project_dir, "sensor_service", "listener.py")

        # Create temporary config with different port
        config_content = f"""
import os
DATA_DIR = "/tmp/sensor_data"
LOG_DIR = os.path.expanduser("~/tools/kent-core/logs")
LISTENER_PORT = {self.test_port}
LISTENER_HOST = "0.0.0.0"
READING_INTERVAL = 0.5
MAX_DATA_AGE = 5.0
ERROR_RETRY_INTERVAL = 1.0
LIDAR_MIN_DISTANCE = 30
LIDAR_MAX_DISTANCE = 4000
LIDAR_RESOLUTION = 64
LIDAR_FREQUENCY = 15
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080
CAMERA_WAIT_TIME = 1000
CURRENT_IMAGE_FILE = "current.jpg"
CURRENT_CSV_FILE = "current.csv"
TIMESTAMP_FILE = "timestamp.txt"
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
READER_PROCESS_NAME = "sensor_reader"
LISTENER_PROCESS_NAME = "sensor_listener"
PROTOCOL_GET_DATA_CMD = "GET_DATA"
PROTOCOL_END_MARKER = "END"
"""

        # Write temporary config
        temp_config = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
        temp_config.write(config_content)
        temp_config.close()

        # Modify listener script to use temp config
        with open(listener_script, 'r') as f:
            listener_code = f.read()

        # Replace config import
        modified_code = listener_code.replace(
            'from sensor_service import config',
            f'sys.path.insert(0, "{os.path.dirname(temp_config.name)}")\nimport {os.path.basename(temp_config.name)[:-3]} as config'
        )

        # Write modified listener
        temp_listener = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
        temp_listener.write(modified_code)
        temp_listener.close()

        # Set environment variables
        env = os.environ.copy()
        env['PYTHONPATH'] = self.project_dir

        proc = subprocess.Popen(
            [python_path, temp_listener.name],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env
        )
        self.processes.append(proc)

        # Store temp file names for cleanup
        self.temp_files = [temp_config.name, temp_listener.name]

        return proc

    def _wait_for_port(self, port, timeout=10):
        """Wait for a port to become available"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(1)
                    result = sock.connect_ex((self.test_host, port))
                    if result == 0:
                        return True
            except:
                pass
            time.sleep(0.5)
        return False

    def _test_connection(self):
        """Test basic connection to the service"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((self.test_host, self.test_port))
                sock.sendall(b"GET_DATA\n")

                # Read some response
                response = sock.recv(1024)
                return len(response) > 0
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False

    def _test_data_retrieval(self):
        """Test full data retrieval"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((self.test_host, self.test_port))
                sock.sendall(b"GET_DATA\n")

                # Read response
                response = b""
                while b"END\n" not in response:
                    chunk = sock.recv(4096)
                    if not chunk:
                        break
                    response += chunk

                # Check if we got a valid response
                response_str = response.decode('utf-8', errors='ignore')
                return ("TIMESTAMP:" in response_str and
                        "IMAGE_SIZE:" in response_str and
                        "CSV_SIZE:" in response_str and
                        "END" in response_str)
        except Exception as e:
            print(f"Data retrieval test failed: {e}")
            return False


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)