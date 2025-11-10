#!/bin/bash
# Reliable Streamlit startup script for EC2
# This script ensures proper environment setup before starting Streamlit

# Don't exit on error - let Streamlit handle its own errors
set +e

# Get the project directory from the current working directory or use default
PROJECT_DIR="${1:-/home/ec2-user/Optimization}"

# Change to project directory
cd "$PROJECT_DIR" || {
  echo "Error: Cannot change to directory $PROJECT_DIR"
  exit 1
}

# Ensure PATH includes user's local bin
export PATH="$HOME/.local/bin:$PATH"

# Start Streamlit (don't use exec - let it run as a child process)
python3 -m streamlit run src/dashboard.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true \
  --server.enableCORS false \
  --server.enableXsrfProtection false

