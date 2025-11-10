#!/bin/bash

# Debug script to check why Streamlit might be stopping

echo "🔍 Debugging Streamlit startup issues..."

cd /home/ec2-user/Optimization

echo ""
echo "1. Checking Python version:"
python3 --version

echo ""
echo "2. Checking if Streamlit is installed:"
python3 -m streamlit --version

echo ""
echo "3. Checking if dashboard.py exists:"
ls -lh src/dashboard.py

echo ""
echo "4. Checking Python syntax:"
python3 -m py_compile src/dashboard.py && echo "✅ Syntax OK" || echo "❌ Syntax error"

echo ""
echo "5. Testing import:"
python3 -c "import sys; sys.path.insert(0, 'src'); import dashboard; print('✅ Import successful')" 2>&1

echo ""
echo "6. Checking for port conflicts:"
netstat -tuln | grep 8501 || echo "Port 8501 is free"

echo ""
echo "7. Checking recent log entries:"
if [ -f dashboard.log ]; then
    echo "Last 30 lines of dashboard.log:"
    tail -30 dashboard.log
else
    echo "No dashboard.log file found"
fi

echo ""
echo "8. Checking running processes:"
ps aux | grep -E "(streamlit|python)" | grep -v grep

echo ""
echo "9. Testing Streamlit run directly (will timeout after 10 seconds):"
timeout 10 python3 -m streamlit run src/dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true 2>&1 | head -50 || echo "Streamlit started but was stopped by timeout"

