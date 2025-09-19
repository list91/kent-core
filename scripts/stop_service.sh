#!/bin/bash

# Stop script for Kent Core Sensor Service
# This script stops both Reader and Listener processes

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_DIR="/tmp/kent-sensor-service"

# Function to stop a process
stop_process() {
    local process_name="$1"
    local pid_file="$PID_DIR/${process_name}.pid"

    if [ ! -f "$pid_file" ]; then
        echo "$process_name is not running (no PID file)"
        return 0
    fi

    local pid=$(cat "$pid_file")

    # Check if process is actually running
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "$process_name is not running (stale PID file)"
        rm -f "$pid_file"
        return 0
    fi

    echo "Stopping $process_name (PID: $pid)..."

    # Send SIGTERM for graceful shutdown
    kill -TERM "$pid"

    # Wait for graceful shutdown
    local count=0
    local max_wait=10
    while [ $count -lt $max_wait ]; do
        if ! kill -0 "$pid" 2>/dev/null; then
            echo "$process_name stopped gracefully"
            rm -f "$pid_file"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        echo -n "."
    done

    echo ""
    echo "Process didn't stop gracefully, sending SIGKILL..."
    kill -KILL "$pid" 2>/dev/null || true

    # Wait a bit more
    sleep 2
    if ! kill -0 "$pid" 2>/dev/null; then
        echo "$process_name stopped forcefully"
        rm -f "$pid_file"
        return 0
    else
        echo "Failed to stop $process_name"
        return 1
    fi
}

echo "=== Stopping Kent Core Sensor Service ==="

# Stop Listener first (to stop accepting new connections)
stop_process "sensor_listener"

# Stop Reader
stop_process "sensor_reader"

# Clean up PID directory if empty
if [ -d "$PID_DIR" ] && [ -z "$(ls -A "$PID_DIR")" ]; then
    rmdir "$PID_DIR"
fi

echo ""
echo "=== Kent Core Sensor Service Stopped ==="