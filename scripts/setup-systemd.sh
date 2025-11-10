#!/bin/bash

# Systemd Service Setup Script for Streamlit Optimization App
# This script sets up Streamlit as a systemd service for automatic restarts

set -e

echo "🔧 Setting up systemd service for Streamlit Optimization App..."

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  This script needs sudo privileges. Please run with sudo."
    echo "Usage: sudo ./scripts/setup-systemd.sh"
    exit 1
fi

PROJECT_DIR="/home/ec2-user/Optimization"
SERVICE_FILE="/etc/systemd/system/streamlit-optimization.service"

# Check if project directory exists
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ Project directory not found: $PROJECT_DIR"
    exit 1
fi

# Check if service file exists in project
if [ ! -f "$PROJECT_DIR/streamlit-optimization.service" ]; then
    echo "❌ Service file not found: $PROJECT_DIR/streamlit-optimization.service"
    exit 1
fi

# Copy service file
echo "📋 Copying service file..."
cp "$PROJECT_DIR/streamlit-optimization.service" "$SERVICE_FILE"

# Reload systemd
echo "🔄 Reloading systemd daemon..."
systemctl daemon-reload

# Enable service (start on boot)
echo "✅ Enabling service (will start on boot)..."
systemctl enable streamlit-optimization.service

# Check if service is already running
if systemctl is-active --quiet streamlit-optimization.service; then
    echo "⚠️  Service is already running. Restarting..."
    systemctl restart streamlit-optimization.service
else
    echo "🚀 Starting service..."
    systemctl start streamlit-optimization.service
fi

# Wait a moment
sleep 3

# Check status
echo ""
echo "📊 Service Status:"
systemctl status streamlit-optimization.service --no-pager -l

echo ""
echo "✅ Systemd service setup complete!"
echo ""
echo "📝 Useful commands:"
echo "   Start:   sudo systemctl start streamlit-optimization.service"
echo "   Stop:    sudo systemctl stop streamlit-optimization.service"
echo "   Restart: sudo systemctl restart streamlit-optimization.service"
echo "   Status:  sudo systemctl status streamlit-optimization.service"
echo "   Logs:    sudo journalctl -u streamlit-optimization.service -f"
echo ""

