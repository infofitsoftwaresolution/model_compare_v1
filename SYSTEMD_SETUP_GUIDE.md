# Systemd Setup Guide - Run on EC2

Follow these steps **on your EC2 instance** to set up the systemd service for reliable deployments.

## Step 1: Clean Up Existing Processes

```bash
# Stop everything completely
sudo pkill -f streamlit
sudo pkill -f python3
sleep 5

# Check if anything is still running
ps aux | grep streamlit
ps aux | grep python3

# Clear any existing logs
cd /home/ec2-user/Optimization
> dashboard.log
```

## Step 2: Create Systemd Service

```bash
sudo tee /etc/systemd/system/streamlit-optimization.service > /dev/null <<'EOF'
[Unit]
Description=Streamlit Optimization App
After=network.target

[Service]
Type=simple
User=ec2-user
Group=ec2-user
WorkingDirectory=/home/ec2-user/Optimization
Environment=PATH=/home/ec2-user/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/home/ec2-user/.local/bin/streamlit run src/dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true --server.runOnSave true --browser.gatherUsageStats false
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
```

## Step 3: Enable and Start Service

```bash
# Reload systemd and enable the service
sudo systemctl daemon-reload
sudo systemctl enable streamlit-optimization.service

# Start the service
sudo systemctl start streamlit-optimization.service

# Check status
sudo systemctl status streamlit-optimization.service
```

## Step 4: Verify It's Working

```bash
# Check service status
sudo systemctl status streamlit-optimization.service

# Check logs
sudo journalctl -u streamlit-optimization.service -f

# Test the app
curl -I http://localhost:8501

# Test public URL
curl -I http://3.111.36.145
```

## Step 5: Test Deployment Script

```bash
cd /home/ec2-user/Optimization
chmod +x scripts/*.sh
./scripts/deploy.sh
```

## Step 6: Verify Nginx (if using)

```bash
# Check nginx config
sudo nginx -t

# Check nginx status
sudo systemctl status nginx

# If nginx is not running, start it
sudo systemctl start nginx
sudo systemctl enable nginx

# Test public access
curl http://3.111.36.145
```

## Troubleshooting

### If service fails to start:

```bash
# Check logs
sudo journalctl -u streamlit-optimization.service -n 50 --no-pager

# Check what's running on port 8501
sudo netstat -tlnp | grep 8501

# Verify Streamlit path
which streamlit
/home/ec2-user/.local/bin/streamlit --version
```

### If port is already in use:

```bash
# Find what's using port 8501
sudo lsof -i :8501
# or
sudo netstat -tlnp | grep 8501

# Kill the process
sudo kill -9 <PID>
```

## Quick Commands Reference

```bash
# Start service
sudo systemctl start streamlit-optimization.service

# Stop service
sudo systemctl stop streamlit-optimization.service

# Restart service
sudo systemctl restart streamlit-optimization.service

# Check status
sudo systemctl status streamlit-optimization.service

# View logs
sudo journalctl -u streamlit-optimization.service -f

# View last 50 lines
sudo journalctl -u streamlit-optimization.service -n 50 --no-pager
```

## After Setup

Once systemd is set up, your GitHub Actions deployment will automatically:
1. Pull latest code
2. Install dependencies
3. Restart the systemd service
4. Verify deployment

**No manual intervention needed!** 🎉

