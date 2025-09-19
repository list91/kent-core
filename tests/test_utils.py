#!/usr/bin/env python3
"""
Unit tests for sensor service utilities
"""

import unittest
import tempfile
import os
import time
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sensor_service import utils


class TestUtils(unittest.TestCase):
    """Test utility functions"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_save_file_atomic(self):
        """Test atomic file saving"""
        test_file = os.path.join(self.test_dir, "test.txt")
        test_data = b"Hello, World!"

        # Test successful save
        result = utils.save_file_atomic(test_file, test_data)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(test_file))

        with open(test_file, 'rb') as f:
            saved_data = f.read()
        self.assertEqual(saved_data, test_data)

    def test_save_text_atomic(self):
        """Test atomic text saving"""
        test_file = os.path.join(self.test_dir, "test.txt")
        test_text = "Hello, World! 🌍"

        # Test successful save
        result = utils.save_text_atomic(test_file, test_text)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(test_file))

        with open(test_file, 'r', encoding='utf-8') as f:
            saved_text = f.read()
        self.assertEqual(saved_text, test_text)

    def test_is_data_stale(self):
        """Test data staleness checking"""
        current_time = time.time()

        # Fresh data
        self.assertFalse(utils.is_data_stale(current_time, 5.0))
        self.assertFalse(utils.is_data_stale(current_time - 2.0, 5.0))

        # Stale data
        self.assertTrue(utils.is_data_stale(current_time - 10.0, 5.0))
        self.assertTrue(utils.is_data_stale(current_time - 6.0, 5.0))

        # Edge case
        self.assertFalse(utils.is_data_stale(current_time - 5.0, 5.0))

    def test_ensure_directory(self):
        """Test directory creation"""
        test_subdir = os.path.join(self.test_dir, "subdir", "nested")

        # Test creating nested directory
        result = utils.ensure_directory(test_subdir)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(test_subdir))
        self.assertTrue(os.path.isdir(test_subdir))

        # Test with existing directory
        result = utils.ensure_directory(test_subdir)
        self.assertTrue(result)

    def test_load_current_data(self):
        """Test loading current sensor data"""
        # Create test data files
        timestamp = time.time()
        image_data = b"fake image data"
        csv_data = "fake,csv,data\n1,2,3"

        # Save test files
        utils.save_text_atomic(os.path.join(self.test_dir, "timestamp.txt"), str(timestamp))
        utils.save_file_atomic(os.path.join(self.test_dir, "current.jpg"), image_data)
        utils.save_text_atomic(os.path.join(self.test_dir, "current.csv"), csv_data)

        # Load data
        result = utils.load_current_data(self.test_dir)
        self.assertIsNotNone(result)

        loaded_timestamp, loaded_image, loaded_csv = result
        self.assertAlmostEqual(loaded_timestamp, timestamp, places=2)
        self.assertEqual(loaded_image, image_data)
        self.assertEqual(loaded_csv, csv_data)

    def test_load_current_data_missing_files(self):
        """Test loading data when files are missing"""
        # Test with empty directory
        result = utils.load_current_data(self.test_dir)
        self.assertIsNone(result)

        # Test with partial files
        utils.save_text_atomic(os.path.join(self.test_dir, "timestamp.txt"), str(time.time()))
        result = utils.load_current_data(self.test_dir)
        self.assertIsNone(result)


class TestLogging(unittest.TestCase):
    """Test logging setup"""

    def setUp(self):
        """Set up test environment"""
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test environment"""
        import shutil
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_setup_logging(self):
        """Test logger setup"""
        log_file = os.path.join(self.test_dir, "test.log")
        logger = utils.setup_logging("test_logger", log_file, "INFO")

        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "test_logger")

        # Test logging
        logger.info("Test message")

        # Check if log file was created
        self.assertTrue(os.path.exists(log_file))

        # Check log content
        with open(log_file, 'r') as f:
            log_content = f.read()
        self.assertIn("Test message", log_content)
        self.assertIn("INFO", log_content)


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)