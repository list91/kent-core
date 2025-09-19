#!/bin/bash

# Installation script for Kent Core Sensor Service
# This script sets up the Python environment and dependencies

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "=== Kent Core Sensor Service Installation ==="
echo "Project directory: $PROJECT_DIR"

# Check if we're on Raspberry Pi
if ! grep -q "Raspberry Pi" /proc/device-tree/model 2>/dev/null; then
    echo "Warning: This doesn't appear to be a Raspberry Pi"
    echo "Some sensor functionality may not work"
fi

# Check Python version
python_cmd=""
for cmd in python3.11 python3.10 python3.9 python3; do
    if command -v "$cmd" >/dev/null 2>&1; then
        version=$("$cmd" --version 2>&1 | cut -d' ' -f2)
        echo "Found Python: $cmd (version $version)"
        python_cmd="$cmd"
        break
    fi
done

if [ -z "$python_cmd" ]; then
    echo "Error: Python 3.9+ not found"
    echo "Please install Python 3.9 or newer"
    exit 1
fi

# Create virtual environment if it doesn't exist
venv_dir="$PROJECT_DIR/venv"
if [ ! -d "$venv_dir" ]; then
    echo "Creating Python virtual environment..."
    "$python_cmd" -m venv "$venv_dir"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
source "$venv_dir/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install base requirements
echo "Installing base Python packages..."
pip install numpy

# Check and install VL53L5CX library
echo "Checking for VL53L5CX library..."
if ! python -c "import vl53l5cx" 2>/dev/null; then
    echo "VL53L5CX library not found"
    echo "Please install it manually if you have the sensor:"
    echo "  cd /path/to/vl53l5cx-python"
    echo "  source $venv_dir/bin/activate"
    echo "  pip install ."
else
    echo "VL53L5CX library found ✓"
fi

# Check for camera tools
echo "Checking for camera tools..."
if command -v libcamera-still >/dev/null 2>&1; then
    echo "libcamera-still found ✓"
else
    echo "libcamera-still not found"
    echo "Please install camera tools:"
    echo "  sudo apt update"
    echo "  sudo apt install libcamera-apps"
fi

# Check for netcat (for status checking)
if ! command -v nc >/dev/null 2>&1; then
    echo "Installing netcat for network checks..."
    sudo apt update
    sudo apt install -y netcat-openbsd
fi

# Create necessary directories
echo "Creating directories..."
mkdir -p "$PROJECT_DIR/logs"
mkdir -p "/tmp/sensor_data"

# Make scripts executable
echo "Making scripts executable..."
chmod +x "$SCRIPT_DIR"/*.sh

# Set up systemd service (optional)
read -p "Do you want to install systemd service for auto-start? (y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "Creating systemd service..."

    cat > "/tmp/kent-sensor-service.service" << EOF
[Unit]
Description=Kent Core Sensor Service
After=network.target
Wants=network.target

[Service]
Type=forking
User=$USER
Group=$USER
WorkingDirectory=$PROJECT_DIR
ExecStart=$SCRIPT_DIR/start_service.sh
ExecStop=$SCRIPT_DIR/stop_service.sh
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

    sudo mv "/tmp/kent-sensor-service.service" "/etc/systemd/system/"
    sudo systemctl daemon-reload
    sudo systemctl enable kent-sensor-service

    echo "Systemd service installed and enabled"
    echo "Use: sudo systemctl start kent-sensor-service"
    echo "     sudo systemctl stop kent-sensor-service"
    echo "     sudo systemctl status kent-sensor-service"
fi

echo ""
echo "=== Installation Complete ==="
echo ""
echo "Next steps:"
echo "1. Test the service:"
echo "   $SCRIPT_DIR/start_service.sh"
echo "   $SCRIPT_DIR/status.sh"
echo ""
echo "2. Test client connection:"
echo "   cd $PROJECT_DIR/tests"
echo "   python test_client.py"
echo ""
echo "3. View logs:"
echo "   tail -f $PROJECT_DIR/logs/sensor_reader.log"
echo "   tail -f $PROJECT_DIR/logs/sensor_listener.log"
echo ""
echo "Note: Make sure your sensors are properly connected before starting"