#!/bin/bash

# Daemon-style Streamlit startup script
# This ensures Streamlit stays running even after SSH session ends

set -e  # Exit on error

cd /home/ec2-user/Optimization || {
    echo "❌ Failed to change to project directory"
    exit 1
}

# Ensure PATH is set
export PATH="$HOME/.local/bin:$PATH"

echo "📂 Current directory: $(pwd)"
echo "🔍 PATH: $PATH"

# Kill any existing Streamlit processes (don't fail if none exist)
pkill -f "streamlit run" || true
sleep 2

# Clear log
> dashboard.log

echo "🚀 Starting Streamlit with setsid..."

# Start Streamlit using setsid to detach from terminal
# This ensures it runs even if the parent process exits
setsid bash -c "cd /home/ec2-user/Optimization && export PATH=\"\$HOME/.local/bin:\$PATH\" && python3 -m streamlit run src/dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --server.runOnSave false --browser.serverAddress 0.0.0.0 --browser.gatherUsageStats false" > dashboard.log 2>&1 &

# Get the PID of the setsid process
SETSID_PID=$!
echo "Setsid process PID: $SETSID_PID"
echo $SETSID_PID > streamlit.pid

# Wait a moment for Streamlit to start
sleep 5

# Check if Streamlit process is running (use pgrep since setsid creates new session)
if pgrep -f "streamlit run" > /dev/null; then
    ACTUAL_PID=$(pgrep -f "streamlit run" | head -1)
    echo "✅ Streamlit started successfully with PID: $ACTUAL_PID"
    echo "📝 Logs: tail -f dashboard.log"
    exit 0
else
    echo "❌ Streamlit process not found after startup"
    echo "📝 Checking logs:"
    if [ -f dashboard.log ]; then
        cat dashboard.log
    else
        echo "No log file found"
    fi
    exit 1
fi

