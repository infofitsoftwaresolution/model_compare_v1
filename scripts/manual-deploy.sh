#!/bin/bash

echo "🚀 Starting manual deployment..."

cd /home/ec2-user/Optimization

# Pull latest code
echo "📥 Pulling latest code..."
git pull origin main

# Install dependencies
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt

# Stop existing Streamlit process gracefully
echo "🛑 Stopping existing Streamlit app..."
pkill -f "streamlit run" || true
sleep 8

# Force kill any remaining processes
pkill -9 -f "streamlit run" || true
sleep 2

# Clear logs
> dashboard.log

# Start new process
echo "🎯 Starting Streamlit app..."
export PATH="$HOME/.local/bin:$PATH"
nohup python3 -m streamlit run src/dashboard.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.runOnSave false \
  --browser.serverAddress "0.0.0.0" \
  --browser.gatherUsageStats false \
  > dashboard.log 2>&1 &

# Wait for app to start
echo "⏳ Waiting for app to start..."
for i in {1..20}; do
    if curl -f -s http://localhost:8501/ > /dev/null 2>&1; then
        echo "✅ Streamlit app started successfully!"
        break
    fi
    echo "   Attempt $i/20 - waiting..."
    sleep 3
done

# Final check
if pgrep -f "streamlit run" > /dev/null; then
    echo "✅ Deployment completed!"
    echo "🌐 App is available at: http://3.111.36.145"
    echo "📝 Logs: tail -f /home/ec2-user/Optimization/dashboard.log"
    echo "🔄 Process ID: $(pgrep -f 'streamlit run')"
else
    echo "❌ Deployment failed - Streamlit process not found"
    echo "🔍 Check logs: tail -f /home/ec2-user/Optimization/dashboard.log"
    exit 1
fi
