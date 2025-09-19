#!/usr/bin/env python3
"""
Test client for Kent Core Sensor Service
"""

import socket
import time
import os
import argparse
from typing import Tuple, Optional


class SensorClient:
    """Client for connecting to sensor service and retrieving data"""

    def __init__(self, host='localhost', port=5555, timeout=10):
        self.host = host
        self.port = port
        self.timeout = timeout

    def get_sensor_data(self) -> Optional[Tuple[float, bytes, str]]:
        """
        Get current sensor data from the service

        Returns:
            Tuple of (timestamp, image_data, csv_data) or None if error
        """
        try:
            # Connect to server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(self.timeout)
                sock.connect((self.host, self.port))

                # Send request
                sock.sendall(b"GET_DATA\n")

                # Read response
                response_data = self._read_response(sock)
                return self._parse_response(response_data)

        except socket.timeout:
            print(f"Timeout connecting to {self.host}:{self.port}")
            return None
        except ConnectionRefused:
            print(f"Connection refused to {self.host}:{self.port}")
            print("Is the sensor service running?")
            return None
        except Exception as e:
            print(f"Error connecting to sensor service: {e}")
            return None

    def _read_response(self, sock) -> bytes:
        """Read the complete response from socket"""
        response = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response += chunk
            # Check if we've received the end marker
            if b"END\n" in response:
                break
        return response

    def _parse_response(self, response_data: bytes) -> Optional[Tuple[float, bytes, str]]:
        """Parse the response data according to protocol"""
        try:
            # Convert to string for parsing headers
            response_str = response_data.decode('utf-8', errors='ignore')

            # Check for error response
            if response_str.startswith("ERROR:"):
                print(f"Server error: {response_str.strip()}")
                return None

            lines = response_str.split('\n')

            # Parse timestamp
            timestamp_line = lines[0]
            if not timestamp_line.startswith("TIMESTAMP:"):
                raise ValueError("Invalid response format - missing timestamp")
            timestamp = float(timestamp_line.split(":", 1)[1])

            # Parse image size
            image_size_line = lines[1]
            if not image_size_line.startswith("IMAGE_SIZE:"):
                raise ValueError("Invalid response format - missing image size")
            image_size = int(image_size_line.split(":", 1)[1])

            # Find where binary data starts (after IMAGE_SIZE line)
            header_end = response_data.find(b'\n', response_data.find(b'IMAGE_SIZE:')) + 1

            # Extract image data
            image_data = response_data[header_end:header_end + image_size]

            # Find CSV size line (after image data)
            csv_start = header_end + image_size
            csv_size_start = response_data.find(b'CSV_SIZE:', csv_start)
            csv_size_end = response_data.find(b'\n', csv_size_start)

            csv_size_line = response_data[csv_size_start:csv_size_end].decode('utf-8')
            csv_size = int(csv_size_line.split(":", 1)[1])

            # Extract CSV data
            csv_data_start = csv_size_end + 1
            csv_data = response_data[csv_data_start:csv_data_start + csv_size].decode('utf-8')

            return timestamp, image_data, csv_data

        except Exception as e:
            print(f"Error parsing response: {e}")
            return None


def save_data_to_files(timestamp: float, image_data: bytes, csv_data: str, output_dir: str = "."):
    """Save received data to files"""
    import datetime

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Generate filenames with timestamp
    dt = datetime.datetime.fromtimestamp(timestamp)
    timestamp_str = dt.strftime("%Y%m%d_%H%M%S")

    # Save image
    image_path = os.path.join(output_dir, f"received_image_{timestamp_str}.jpg")
    with open(image_path, 'wb') as f:
        f.write(image_data)
    print(f"Image saved: {image_path} ({len(image_data)} bytes)")

    # Save CSV
    csv_path = os.path.join(output_dir, f"received_lidar_{timestamp_str}.csv")
    with open(csv_path, 'w') as f:
        f.write(csv_data)
    print(f"CSV saved: {csv_path} ({len(csv_data)} bytes)")


def analyze_csv_data(csv_data: str):
    """Analyze LiDAR CSV data and print statistics"""
    lines = csv_data.strip().split('\n')

    # Skip comment lines and headers
    data_lines = [line for line in lines if not line.startswith('#') and ',' in line and not line.startswith('Row\\Col')]

    if not data_lines:
        print("No LiDAR data found in CSV")
        return

    # Parse numeric values
    valid_distances = []
    invalid_count = 0
    total_points = 0

    for line in data_lines:
        values = line.split(',')[1:]  # Skip row label
        for val in values:
            try:
                distance = float(val)
                total_points += 1
                if distance == -1:
                    invalid_count += 1
                else:
                    valid_distances.append(distance)
            except ValueError:
                continue

    print(f"\nLiDAR Data Analysis:")
    print(f"  Total points: {total_points}")
    print(f"  Valid points: {len(valid_distances)} ({len(valid_distances)/total_points*100:.1f}%)")
    print(f"  Invalid points: {invalid_count} ({invalid_count/total_points*100:.1f}%)")

    if valid_distances:
        print(f"  Distance range: {min(valid_distances):.0f} - {max(valid_distances):.0f} mm")
        print(f"  Average distance: {sum(valid_distances)/len(valid_distances):.0f} mm")


def main():
    parser = argparse.ArgumentParser(description="Test client for Kent Core Sensor Service")
    parser.add_argument("--host", default="localhost", help="Server host (default: localhost)")
    parser.add_argument("--port", type=int, default=5555, help="Server port (default: 5555)")
    parser.add_argument("--timeout", type=int, default=10, help="Connection timeout in seconds")
    parser.add_argument("--save", action="store_true", help="Save received data to files")
    parser.add_argument("--output-dir", default="./received_data", help="Output directory for saved files")
    parser.add_argument("--continuous", "-c", action="store_true", help="Continuously request data")
    parser.add_argument("--interval", type=float, default=1.0, help="Interval between requests in continuous mode")

    args = parser.parse_args()

    print(f"=== Kent Core Sensor Service Test Client ===")
    print(f"Connecting to: {args.host}:{args.port}")
    print()

    client = SensorClient(args.host, args.port, args.timeout)

    try:
        iteration = 0
        while True:
            iteration += 1
            print(f"--- Request {iteration} ---")

            # Get data
            start_time = time.time()
            result = client.get_sensor_data()
            request_time = time.time() - start_time

            if result:
                timestamp, image_data, csv_data = result

                # Calculate data age
                data_age = time.time() - timestamp

                print(f"✓ Data received successfully")
                print(f"  Request time: {request_time:.2f}s")
                print(f"  Data timestamp: {timestamp:.2f}")
                print(f"  Data age: {data_age:.2f}s")
                print(f"  Image size: {len(image_data)} bytes")
                print(f"  CSV size: {len(csv_data)} bytes")

                # Analyze CSV data
                analyze_csv_data(csv_data)

                # Save to files if requested
                if args.save:
                    save_data_to_files(timestamp, image_data, csv_data, args.output_dir)

            else:
                print("✗ Failed to get data")

            # Break if not continuous mode
            if not args.continuous:
                break

            print(f"\nWaiting {args.interval}s before next request...\n")
            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Unexpected error: {e}")


if __name__ == "__main__":
    main()