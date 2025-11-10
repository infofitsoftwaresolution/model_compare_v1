# Systemd Service Setup (Optional but Recommended)

This guide shows how to set up Streamlit as a systemd service for better process management and automatic restarts.

## Setup Instructions

SSH into your EC2 instance and run:

```bash
# Copy the service file
sudo cp /home/ec2-user/Optimization/streamlit-optimization.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable the service (starts on boot)
sudo systemctl enable streamlit-optimization.service

# Start the service
sudo systemctl start streamlit-optimization.service

# Check status
sudo systemctl status streamlit-optimization.service
```

## Service Management Commands

```bash
# Start the service
sudo systemctl start streamlit-optimization.service

# Stop the service
sudo systemctl stop streamlit-optimization.service

# Restart the service
sudo systemctl restart streamlit-optimization.service

# Check status
sudo systemctl status streamlit-optimization.service

# View logs
sudo journalctl -u streamlit-optimization.service -f
```

## Benefits

- **Automatic restarts** - Service restarts automatically if it crashes
- **Boot persistence** - Starts automatically on system reboot
- **Better logging** - Centralized logging via journalctl
- **Process management** - Managed by systemd instead of nohup

## Note

If you use systemd service, you may want to update your deployment scripts to use:
```bash
sudo systemctl restart streamlit-optimization.service
```
instead of manually starting with nohup.

