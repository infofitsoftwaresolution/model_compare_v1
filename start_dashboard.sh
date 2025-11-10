#!/bin/bash
# Linux/Mac shell script to start the dashboard
# This script activates the virtual environment and starts Streamlit

echo "Starting AI Cost Optimizer Dashboard..."

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Virtual environment not found!"
    echo "Please run: python3 -m venv .venv"
    echo "Then install dependencies: pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if dependencies are installed
python -c "import streamlit" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Dependencies not installed!"
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Start Streamlit dashboard
echo "Starting dashboard..."
streamlit run src/dashboard.py
