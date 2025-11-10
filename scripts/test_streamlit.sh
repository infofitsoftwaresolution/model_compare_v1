#!/bin/bash
# Test script to diagnose Streamlit startup issues

PROJECT_DIR="/home/ec2-user/Optimization"
cd "$PROJECT_DIR"

echo "=== Streamlit Diagnostic Test ==="
echo ""

echo "1. Checking Python version:"
python3 --version
echo ""

echo "2. Checking if Streamlit is installed:"
python3 -m streamlit --version
echo ""

echo "3. Checking PATH:"
echo "PATH=$PATH"
echo ""

echo "4. Checking if dashboard.py exists:"
ls -la src/dashboard.py
echo ""

echo "5. Testing Python import:"
python3 -c "import sys; sys.path.insert(0, '.'); from src import dashboard; print('✅ Dashboard imports successfully')" 2>&1
echo ""

echo "6. Testing Streamlit run (will timeout after 5 seconds):"
timeout 5 python3 -m streamlit run src/dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true 2>&1 || echo "Streamlit started (timeout expected)"
echo ""

echo "=== Diagnostic Complete ==="

