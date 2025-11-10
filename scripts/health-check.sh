#!/bin/bash

# Health check for Streamlit app
echo "🔍 Performing health check..."

# Check if Streamlit process is running
if pgrep -f "streamlit run" > /dev/null; then
    PID=$(pgrep -f "streamlit run" | head -1)
    echo "✅ Streamlit process is running"
    echo "   PID: $PID"
    
    # Check if port 8501 is accessible
    if netstat -tuln 2>/dev/null | grep ':8501' > /dev/null || ss -tuln 2>/dev/null | grep ':8501' > /dev/null; then
        echo "✅ Port 8501 is listening"
        
        # Try to access the app
        if curl -f -s --max-time 10 http://localhost:8501/ > /dev/null; then
            echo "✅ Streamlit app is responding"
            echo "🎉 Health check PASSED"
            exit 0
        else
            echo "⚠️  Streamlit app not responding on port 8501"
            echo "📝 Checking logs..."
            tail -20 dashboard.log
        fi
    else
        echo "❌ Port 8501 is not listening"
    fi
else
    echo "❌ Streamlit process not found"
fi

echo "💥 Health check FAILED"
exit 1
