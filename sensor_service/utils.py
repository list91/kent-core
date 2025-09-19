#!/usr/bin/env python3
"""
Utility functions for the sensor service
"""

import os
import tempfile
import shutil
import logging
from typing import Optional, Tuple
import time

def setup_logging(name: str, log_file: str, level: str = "INFO") -> logging.Logger:
    """
    Set up logging for a process

    Args:
        name: Logger name
        log_file: Path to the log file
        level: Logging level

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level))

    # Create formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Add file handler
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger

def save_file_atomic(file_path: str, data: bytes) -> bool:
    """
    Save data to file atomically using temporary file and rename

    Args:
        file_path: Target file path
        data: Data to save

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # Write to temporary file first
        with tempfile.NamedTemporaryFile(mode="wb", dir=os.path.dirname(file_path), delete=False) as temp_file:
            temp_file.write(data)
            temp_path = temp_file.name

        # Atomically rename to target file
        shutil.move(temp_path, file_path)
        return True
    except Exception as e:
        logging.error(f"Failed to save file {file_path}: {e}")
        # Clean up temp file if it exists
        if "temp_path" in locals() and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        return False

def save_text_atomic(file_path: str, text: str) -> bool:
    """
    Save text to file atomically

    Args:
        file_path: Target file path
        text: Text to save

    Returns:
        True if successful, False otherwise
    """
    return save_file_atomic(file_path, text.encode("utf-8"))

def is_data_stale(timestamp: float, max_age: float) -> bool:
    """
    Check if data is stale based on timestamp

    Args:
        timestamp: Unix timestamp of the data
        max_age: Maximum age in seconds

    Returns:
        True if data is stale, False otherwise
    """
    return (time.time() - timestamp) > max_age

def load_current_data(data_dir: str) -> Optional[Tuple[float, bytes, str]]:
    """
    Load current sensor data from files

    Args:
        data_dir: Directory containing the data files

    Returns:
        Tuple of (timestamp, image_data, csv_data) or None if error
    """
    try:
        # Read timestamp
        timestamp_path = os.path.join(data_dir, "timestamp.txt")
        with open(timestamp_path, "r") as f:
            timestamp = float(f.read().strip())

        # Read image
        image_path = os.path.join(data_dir, "current.jpg")
        with open(image_path, "rb") as f:
            image_data = f.read()

        # Read CSV
        csv_path = os.path.join(data_dir, "current.csv")
        with open(csv_path, "r") as f:
            csv_data = f.read()

        return timestamp, image_data, csv_data
    except Exception as e:
        logging.error(f"Failed to load current data: {e}")
        return None

def ensure_directory(path: str) -> bool:
    """
    Ensure a directory exists

    Args:
        path: Directory path

    Returns:
        True if directory exists or was created, False otherwise
    """
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        logging.error(f"Failed to create directory {path}: {e}")
        return False
