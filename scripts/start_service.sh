#!/bin/bash

# Start script for Kent Core Sensor Service
# This script starts both Reader and Listener processes

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PYTHON_ENV="$PROJECT_DIR/venv/bin/python3"
LOG_DIR="$PROJECT_DIR/logs"
PID_DIR="/tmp/kent-sensor-service"

# Check if virtual environment exists
if [ ! -f "$PYTHON_ENV" ]; then
    echo "Error: Python virtual environment not found at $PYTHON_ENV"
    echo "Please run install.sh first"
    exit 1
fi

# Create directories
mkdir -p "$LOG_DIR"
mkdir -p "$PID_DIR"
mkdir -p "/tmp/sensor_data"

# Function to check if process is running
is_process_running() {
    local pid_file="$1"
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # Process is running
        else
            rm -f "$pid_file"  # Remove stale PID file
            return 1  # Process is not running
        fi
    fi
    return 1  # PID file doesn't exist
}

# Function to start a process
start_process() {
    local process_name="$1"
    local script_path="$2"
    local pid_file="$PID_DIR/${process_name}.pid"
    local log_file="$LOG_DIR/${process_name}.log"

    if is_process_running "$pid_file"; then
        echo "$process_name is already running (PID: $(cat "$pid_file"))"
        return 0
    fi

    echo "Starting $process_name..."

    # Start process in background and save PID
    cd "$PROJECT_DIR"
    nohup "$PYTHON_ENV" "$script_path" >> "$log_file" 2>&1 &
    local pid=$!
    echo $pid > "$pid_file"

    # Give it a moment to start
    sleep 2

    # Check if it's still running
    if is_process_running "$pid_file"; then
        echo "$process_name started successfully (PID: $pid)"
        return 0
    else
        echo "Failed to start $process_name"
        return 1
    fi
}

# Function to wait for process to be ready
wait_for_reader() {
    echo "Waiting for Reader to initialize sensors..."
    local max_wait=30
    local count=0

    while [ $count -lt $max_wait ]; do
        if [ -f "/tmp/sensor_data/timestamp.txt" ]; then
            echo "Reader is ready and producing data"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        echo -n "."
    done

    echo ""
    echo "Warning: Reader may not be fully ready (no data detected after ${max_wait}s)"
    return 1
}

# Function to wait for listener to be ready
wait_for_listener() {
    echo "Waiting for Listener to start accepting connections..."
    local max_wait=10
    local count=0

    while [ $count -lt $max_wait ]; do
        if nc -z localhost 5555 2>/dev/null; then
            echo "Listener is ready and accepting connections on port 5555"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        echo -n "."
    done

    echo ""
    echo "Warning: Listener may not be ready (port 5555 not responding after ${max_wait}s)"
    return 1
}

echo "=== Starting Kent Core Sensor Service ==="

# Start Reader process
if ! start_process "sensor_reader" "$PROJECT_DIR/sensor_service/reader.py"; then
    echo "Failed to start Reader process"
    exit 1
fi

# Wait for Reader to initialize
wait_for_reader

# Start Listener process
if ! start_process "sensor_listener" "$PROJECT_DIR/sensor_service/listener.py"; then
    echo "Failed to start Listener process"
    exit 1
fi

# Wait for Listener to be ready
wait_for_listener

echo ""
echo "=== Kent Core Sensor Service Started Successfully ==="
echo "Reader PID: $(cat "$PID_DIR/sensor_reader.pid")"
echo "Listener PID: $(cat "$PID_DIR/sensor_listener.pid")"
echo ""
echo "To check status: $SCRIPT_DIR/status.sh"
echo "To stop service: $SCRIPT_DIR/stop_service.sh"
echo "To view logs: tail -f $LOG_DIR/sensor_reader.log"
echo "             tail -f $LOG_DIR/sensor_listener.log"
echo ""
echo "Service is now listening on port 5555"