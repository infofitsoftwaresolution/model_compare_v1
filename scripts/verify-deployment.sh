#!/bin/bash

# Quick verification script to check if Streamlit is running properly

echo "🔍 Verifying Streamlit deployment..."

cd /home/ec2-user/Optimization

echo ""
echo "1. Checking if Streamlit process is running:"
if pgrep -f "streamlit run" > /dev/null; then
    PID=$(pgrep -f "streamlit run" | head -1)
    echo "   ✅ Streamlit is running (PID: $PID)"
    ps aux | grep "streamlit run" | grep -v grep
else
    echo "   ❌ Streamlit process not found"
    exit 1
fi

echo ""
echo "2. Checking if port 8501 is listening:"
if netstat -tuln | grep ':8501' > /dev/null; then
    echo "   ✅ Port 8501 is listening"
    netstat -tuln | grep ':8501'
else
    echo "   ❌ Port 8501 is not listening"
fi

echo ""
echo "3. Testing HTTP response:"
if curl -f -s --max-time 5 http://localhost:8501/ > /dev/null; then
    echo "   ✅ Streamlit is responding to HTTP requests"
else
    echo "   ⚠️  Streamlit is not responding (may still be starting)"
fi

echo ""
echo "4. Recent log entries:"
if [ -f dashboard.log ]; then
    echo "   Last 10 lines:"
    tail -10 dashboard.log | sed 's/^/   /'
else
    echo "   ⚠️  No log file found"
fi

echo ""
echo "5. Health check:"
./scripts/health-check.sh

echo ""
echo "✅ Verification complete!"
echo "🌐 App should be available at: http://3.111.36.145:8501"

