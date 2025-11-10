#!/bin/bash

set -e

echo "🚀 Starting automated deployment..."

cd /home/ec2-user/Optimization

# Pull latest changes
echo "📥 Pulling latest code from GitHub..."
git fetch origin
git reset --hard origin/main

# Install dependencies
echo "📦 Installing/updating dependencies..."
pip3 install -r requirements.txt

# Restart the Streamlit service
echo "🔄 Restarting Streamlit service..."
sudo systemctl restart streamlit-optimization.service

# Wait for service to start
echo "⏳ Waiting for service to start..."
sleep 10

# Check service status
if sudo systemctl is-active --quiet streamlit-optimization.service; then
    echo "✅ Streamlit service is running"
else
    echo "❌ Streamlit service failed to start"
    sudo systemctl status streamlit-optimization.service
    exit 1
fi

# Health check
echo "🔍 Performing health check..."
for i in {1..10}; do
    if curl -f -s --max-time 5 http://localhost:8501/ > /dev/null; then
        echo "✅ Health check passed - App is responding"
        echo "🎉 Deployment completed successfully!"
        echo "🌐 App is live at: http://3.111.36.145"
        exit 0
    fi
    echo "   Health check attempt $i/10 failed, retrying..."
    sleep 5
done

echo "❌ Health check failed after 10 attempts"
echo "📋 Service status:"
sudo systemctl status streamlit-optimization.service
echo "📝 Recent logs:"
sudo journalctl -u streamlit-optimization.service -n 20 --no-pager
exit 1
