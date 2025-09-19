#!/bin/bash

# Status script for Kent Core Sensor Service
# Shows the current status of Reader and Listener processes

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PID_DIR="/tmp/kent-sensor-service"
LOG_DIR="$PROJECT_DIR/logs"

# Function to check process status
check_process_status() {
    local process_name="$1"
    local pid_file="$PID_DIR/${process_name}.pid"

    printf "%-15s: " "$process_name"

    if [ ! -f "$pid_file" ]; then
        echo "NOT RUNNING (no PID file)"
        return 1
    fi

    local pid=$(cat "$pid_file")

    if kill -0 "$pid" 2>/dev/null; then
        echo "RUNNING (PID: $pid)"
        return 0
    else
        echo "NOT RUNNING (stale PID file)"
        return 1
    fi
}

# Function to check data freshness
check_data_freshness() {
    local data_dir="/tmp/sensor_data"
    local timestamp_file="$data_dir/timestamp.txt"

    printf "%-15s: " "Data freshness"

    if [ ! -f "$timestamp_file" ]; then
        echo "NO DATA (timestamp file missing)"
        return 1
    fi

    local timestamp=$(cat "$timestamp_file" 2>/dev/null)
    if [ -z "$timestamp" ]; then
        echo "NO DATA (invalid timestamp)"
        return 1
    fi

    local current_time=$(date +%s)
    local age=$((current_time - ${timestamp%.*}))  # Remove decimal part

    if [ $age -le 5 ]; then
        echo "FRESH (${age}s old)"
        return 0
    elif [ $age -le 30 ]; then
        echo "STALE (${age}s old)"
        return 1
    else
        echo "VERY STALE (${age}s old)"
        return 1
    fi
}

# Function to check network connectivity
check_network() {
    printf "%-15s: " "Network (5555)"

    if command -v nc >/dev/null 2>&1; then
        if nc -z localhost 5555 2>/dev/null; then
            echo "LISTENING"
            return 0
        else
            echo "NOT LISTENING"
            return 1
        fi
    else
        echo "UNKNOWN (nc not available)"
        return 1
    fi
}

# Function to show file sizes
show_file_info() {
    local data_dir="/tmp/sensor_data"
    echo ""
    echo "Data files:"

    for file in "current.jpg" "current.csv" "timestamp.txt"; do
        local file_path="$data_dir/$file"
        printf "  %-15s: " "$file"

        if [ -f "$file_path" ]; then
            local size=$(stat -c%s "$file_path" 2>/dev/null || echo "unknown")
            local mtime=$(stat -c%Y "$file_path" 2>/dev/null)
            if [ -n "$mtime" ]; then
                local age=$(($(date +%s) - mtime))
                echo "${size} bytes (${age}s old)"
            else
                echo "${size} bytes"
            fi
        else
            echo "MISSING"
        fi
    done
}

# Function to show recent log entries
show_recent_logs() {
    echo ""
    echo "Recent log entries (last 5 lines each):"

    for process in "sensor_reader" "sensor_listener"; do
        local log_file="$LOG_DIR/${process}.log"
        echo ""
        echo "=== $process ==="
        if [ -f "$log_file" ]; then
            tail -n 5 "$log_file"
        else
            echo "(log file not found)"
        fi
    done
}

# Main status check
echo "=== Kent Core Sensor Service Status ==="
echo ""

reader_status=0
listener_status=0
data_status=0
network_status=0

check_process_status "Reader" || reader_status=1
check_process_status "Listener" || listener_status=1
check_data_freshness || data_status=1
check_network || network_status=1

show_file_info

# Overall status
echo ""
echo "Overall status:"
if [ $reader_status -eq 0 ] && [ $listener_status -eq 0 ] && [ $data_status -eq 0 ] && [ $network_status -eq 0 ]; then
    echo "✓ ALL SYSTEMS OPERATIONAL"
else
    echo "⚠ SOME ISSUES DETECTED"
    if [ $reader_status -ne 0 ]; then
        echo "  - Reader process not running"
    fi
    if [ $listener_status -ne 0 ]; then
        echo "  - Listener process not running"
    fi
    if [ $data_status -ne 0 ]; then
        echo "  - Data is stale or missing"
    fi
    if [ $network_status -ne 0 ]; then
        echo "  - Network service not responding"
    fi
fi

# Show recent logs if there are issues
if [ $reader_status -ne 0 ] || [ $listener_status -ne 0 ]; then
    show_recent_logs
fi

echo ""
echo "Commands:"
echo "  Start service: $SCRIPT_DIR/start_service.sh"
echo "  Stop service:  $SCRIPT_DIR/stop_service.sh"
echo "  View logs:     tail -f $LOG_DIR/sensor_reader.log"
echo "                 tail -f $LOG_DIR/sensor_listener.log"