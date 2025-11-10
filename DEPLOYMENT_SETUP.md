# CI/CD Deployment Setup Guide

This guide will help you set up the complete CI/CD pipeline for your Streamlit application on EC2.

## Prerequisites

- EC2 instance running (IP: 3.111.36.145)
- SSH access to EC2 instance
- GitHub repository access
- EC2 SSH private key (.pem file)

## Step 1: Set Up GitHub Secrets

1. Go to your GitHub repository: https://github.com/infofitsoftwaresolution/Optimization
2. Click on **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add these secrets:

   - **Name:** `EC2_SSH_KEY`
     **Value:** Your EC2 private SSH key (the entire content of your .pem file)
   
   - **Name:** `EC2_HOST`
     **Value:** `3.111.36.145`

## Step 2: Update Nginx Configuration on EC2

SSH into your EC2 instance and run:

```bash
sudo tee /etc/nginx/conf.d/optimization-app.conf > /dev/null <<'EOF'
server {
    listen 80;
    server_name 3.111.36.145;
    
    # Increase timeouts for Streamlit
    proxy_connect_timeout 600s;
    proxy_send_timeout 600s;
    proxy_read_timeout 600s;
    fastcgi_send_timeout 600s;
    fastcgi_read_timeout 600s;
    
    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
EOF

# Test and reload nginx
sudo nginx -t
sudo systemctl reload nginx
```

## Step 3: Make Scripts Executable on EC2

SSH into EC2 and run:

```bash
cd /home/ec2-user/Optimization
chmod +x scripts/*.sh
```

## Step 4: Test Manual Deployment

On EC2, test the manual deployment:

```bash
cd /home/ec2-user/Optimization
./scripts/manual-deploy.sh
```

## Step 5: Run Health Check

```bash
./scripts/health-check.sh
```

## Step 6: Verify Setup

```bash
# Check if nginx is running
sudo systemctl status nginx

# Check if Streamlit is running
ps aux | grep streamlit

# Check nginx configuration
sudo nginx -t

# Test the public access
curl http://3.111.36.145
```

## Step 7: Test CI/CD Pipeline

1. Make a small change to any file in your repository
2. Commit and push to main:
   ```bash
   git add .
   git commit -m "Test CI/CD pipeline"
   git push origin main
   ```
3. Go to GitHub Actions tab: https://github.com/infofitsoftwaresolution/Optimization/actions
4. Watch the deployment run automatically!

## How It Works

1. **On Push to Main:**
   - GitHub Actions runs the `test` job
   - If tests pass, the `deploy` job runs
   - The deploy job SSHs into EC2
   - Pulls latest code
   - Installs dependencies
   - Restarts Streamlit app
   - Verifies deployment

2. **Manual Deployment:**
   - Use `./scripts/manual-deploy.sh` on EC2
   - Useful for testing or emergency deployments

3. **Health Check:**
   - Use `./scripts/health-check.sh` to verify app status
   - Checks process, port, and HTTP response

## Troubleshooting

### If deployment fails:

1. Check GitHub Actions logs
2. SSH into EC2 and check logs:
   ```bash
   tail -f /home/ec2-user/Optimization/dashboard.log
   ```
3. Verify Streamlit is running:
   ```bash
   ps aux | grep streamlit
   ```
4. Check nginx status:
   ```bash
   sudo systemctl status nginx
   ```

### If app is not accessible:

1. Check EC2 Security Group - ensure port 80 and 8501 are open
2. Check nginx configuration:
   ```bash
   sudo nginx -t
   ```
3. Check Streamlit is listening:
   ```bash
   netstat -tuln | grep 8501
   ```

## Files Created

- `.github/workflows/deploy.yml` - GitHub Actions workflow
- `scripts/deploy.sh` - Automated deployment script
- `scripts/manual-deploy.sh` - Manual deployment script
- `scripts/health-check.sh` - Health check script
- `tests/test_basic.py` - Basic test suite
- `nginx-optimization-app.conf` - Nginx configuration template

## Next Steps

- Monitor deployments in GitHub Actions
- Set up notifications for deployment status
- Add more comprehensive tests
- Set up monitoring and alerting

