#!/bin/bash

# Fallback script to start Streamlit manually
cd /home/ec2-user/Optimization
export PATH="$HOME/.local/bin:$PATH"

# Kill any existing processes
pkill -f "streamlit run" || true
sleep 3

# Start Streamlit
nohup streamlit run src/dashboard.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.runOnSave true \
  --browser.gatherUsageStats false \
  > dashboard.log 2>&1 &

echo "Streamlit started with PID: $!"
echo "Check logs: tail -f dashboard.log"

