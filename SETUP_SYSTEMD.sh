#!/bin/bash

# Systemd Service Setup Script
# Run this on EC2 to set up the Streamlit service

echo "🔧 Setting up systemd service for Streamlit..."

# Clean up
echo "🧹 Cleaning up existing processes..."
sudo pkill -f streamlit || true
sudo pkill -f python3 || true
sleep 3

# Create service file
echo "📝 Creating systemd service file..."
sudo tee /etc/systemd/system/streamlit-optimization.service > /dev/null <<'EOF'
[Unit]
Description=Streamlit Optimization App
After=network.target

[Service]
Type=simple
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/Optimization
Environment=PATH=/home/ec2-user/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/ec2-user/.local/bin/streamlit run src/dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --server.runOnSave true --browser.gatherUsageStats false
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Verify file was created
if [ -f /etc/systemd/system/streamlit-optimization.service ]; then
    echo "✅ Service file created successfully"
else
    echo "❌ Failed to create service file"
    exit 1
fi

# Reload systemd
echo "🔄 Reloading systemd..."
sudo systemctl daemon-reload

# Enable service
echo "✅ Enabling service..."
sudo systemctl enable streamlit-optimization.service

# Start service
echo "🚀 Starting service..."
sudo systemctl start streamlit-optimization.service

# Wait a moment
sleep 5

# Check status
echo ""
echo "📊 Service Status:"
sudo systemctl status streamlit-optimization.service --no-pager -l

echo ""
echo "✅ Setup complete!"
echo ""
echo "📝 Useful commands:"
echo "   Status:  sudo systemctl status streamlit-optimization.service"
echo "   Logs:    sudo journalctl -u streamlit-optimization.service -f"
echo "   Restart: sudo systemctl restart streamlit-optimization.service"

