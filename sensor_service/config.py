#!/usr/bin/env python3
"""
Configuration settings for the sensor service
"""

import os

# Paths
DATA_DIR = "/tmp/sensor_data"
LOG_DIR = os.path.expanduser("~/tools/kent-core/logs")

# Network settings
LISTENER_PORT = 5555
LISTENER_HOST = "0.0.0.0"

# Timing settings (in seconds)
READING_INTERVAL = 0.5      # Interval between sensor readings
MAX_DATA_AGE = 5.0          # Maximum age of data before considered stale
ERROR_RETRY_INTERVAL = 1.0  # Retry interval after an error

# LiDAR sensor settings
LIDAR_MIN_DISTANCE = 30     # Minimum valid distance in mm
LIDAR_MAX_DISTANCE = 4000   # Maximum valid distance in mm
LIDAR_RESOLUTION = 64       # 8x8 resolution
LIDAR_FREQUENCY = 15        # Hz

# Camera settings
CAMERA_WIDTH = 1920
CAMERA_HEIGHT = 1080
CAMERA_WAIT_TIME = 1000     # Milliseconds to wait for camera

# File names for current data
CURRENT_IMAGE_FILE = "current.jpg"
CURRENT_CSV_FILE = "current.csv"
TIMESTAMP_FILE = "timestamp.txt"

# Logging settings
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Process settings
READER_PROCESS_NAME = "sensor_reader"
LISTENER_PROCESS_NAME = "sensor_listener"

# Protocol settings
PROTOCOL_GET_DATA_CMD = "GET_DATA"
PROTOCOL_END_MARKER = "END"
