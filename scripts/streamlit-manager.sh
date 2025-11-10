#!/bin/bash

case "$1" in
    start)
        echo "Starting Streamlit app..."
        cd /home/ec2-user/Optimization
        export PATH="$HOME/.local/bin:$PATH"
        nohup python3 -m streamlit run src/dashboard.py \
          --server.port 8501 \
          --server.address 0.0.0.0 \
          --server.headless true \
          --server.runOnSave false \
          --browser.serverAddress "0.0.0.0" \
          --browser.gatherUsageStats false \
          > dashboard.log 2>&1 &
        echo $! > streamlit.pid
        echo "Streamlit started with PID: $(cat streamlit.pid)"
        ;;
    stop)
        echo "Stopping Streamlit app..."
        if [ -f streamlit.pid ]; then
            kill -TERM $(cat streamlit.pid) 2>/dev/null
            rm -f streamlit.pid
        fi
        pkill -f "streamlit run"
        sleep 5
        pkill -9 -f "streamlit run" 2>/dev/null
        echo "Streamlit app stopped"
        ;;
    restart)
        $0 stop
        sleep 5
        $0 start
        ;;
    status)
        if pgrep -f "streamlit run" > /dev/null; then
            echo "Streamlit app is running"
            ps aux | grep "streamlit run" | grep -v grep
        else
            echo "Streamlit app is not running"
        fi
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

