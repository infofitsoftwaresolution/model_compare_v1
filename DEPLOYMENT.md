# 🚀 CI/CD Deployment Guide

This guide explains how to set up automated deployment from GitHub to EC2 for the Optimization project.

## 📋 Prerequisites

1. **EC2 Instance** running Ubuntu (IP: 3.110.44.41)
2. **GitHub Repository**: https://github.com/infofitsoftwaresolution/Optimization
3. **SSH Access** to EC2 instance
4. **GitHub Account** with repository access

---

## 🔧 Step 1: Initial EC2 Setup

SSH into your EC2 instance and run the setup script:

```bash
ssh ubuntu@3.110.44.41
cd ~
wget https://raw.githubusercontent.com/infofitsoftwaresolution/Optimization/main/scripts/ec2_setup.sh
chmod +x ec2_setup.sh
./ec2_setup.sh
```

Or manually copy the script and run it.

**What this script does:**
- Installs Python 3, pip, git, nginx
- Installs Python dependencies
- Clones the repository
- Configures nginx as reverse proxy
- Sets up firewall rules
- Creates systemd service for Streamlit

---

## 🔐 Step 2: Configure GitHub Secrets

You need to add the following secrets to your GitHub repository:

1. Go to your GitHub repository: https://github.com/infofitsoftwaresolution/Optimization
2. Click on **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add the following:

### Required Secrets:

#### `EC2_HOST`
- **Value**: `3.110.44.41`
- **Description**: Your EC2 instance IP address

#### `EC2_USER`
- **Value**: `ubuntu` (or your EC2 username)
- **Description**: SSH username for EC2 instance

#### `SSH_PRIVATE_KEY`
- **Value**: Your private SSH key content
- **Description**: Private SSH key to access EC2 instance

**How to get your SSH private key:**
```bash
# On your local machine, if you have the key file:
cat ~/.ssh/your-ec2-key.pem

# Copy the entire output including:
# -----BEGIN RSA PRIVATE KEY-----
# ... (all the content) ...
# -----END RSA PRIVATE KEY-----
```

#### `EC2_SSH_PORT` (Optional)
- **Value**: `22` (default)
- **Description**: SSH port (only if using non-standard port)

---

## 🔑 Step 3: Generate SSH Key Pair (If Needed)

If you don't have an SSH key pair for EC2:

### On Your Local Machine:

```bash
# Generate new SSH key pair
ssh-keygen -t rsa -b 4096 -C "infofitsoftware@gmail.com" -f ~/.ssh/ec2_optimization_key

# Copy public key to EC2
ssh-copy-id -i ~/.ssh/ec2_optimization_key.pub ubuntu@3.110.44.41

# Or manually add to EC2:
cat ~/.ssh/ec2_optimization_key.pub | ssh ubuntu@3.110.44.41 "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"
```

### Add Private Key to GitHub Secrets:

```bash
# Display private key (copy entire output)
cat ~/.ssh/ec2_optimization_key
```

Copy the entire output (including `-----BEGIN` and `-----END` lines) and paste it as the `SSH_PRIVATE_KEY` secret in GitHub.

---

## ⚙️ Step 4: Configure Git User Email

To ensure all commits use the correct email:

### On Your Local Machine:

```bash
cd /path/to/Optimization
git config user.email "infofitsoftware@gmail.com"
git config user.name "InfoFit Software"
```

### Or use the provided script:

```bash
chmod +x scripts/setup_git_config.sh
./scripts/setup_git_config.sh
```

### For Global Configuration (All Repositories):

```bash
git config --global user.email "infofitsoftware@gmail.com"
git config --global user.name "InfoFit Software"
```

---

## 🚀 Step 5: Test Deployment

1. **Make a test change** to any file
2. **Commit and push** to main branch:

```bash
git add .
git commit -m "Test: CI/CD deployment"
git push origin main
```

3. **Monitor deployment**:
   - Go to GitHub repository → **Actions** tab
   - Watch the workflow run
   - Check deployment logs

4. **Verify deployment**:
   - Access dashboard: http://3.110.44.41:8501
   - Check application logs on EC2:
     ```bash
     ssh ubuntu@3.110.44.41
     tail -f /home/ubuntu/Optimization/dashboard.log
     ```

---

## 🔄 How It Works

### Automatic Deployment Flow:

1. **Push to main/master branch** → Triggers GitHub Actions workflow
2. **Test Job** → Runs syntax checks and verifies files
3. **Deploy Job** → SSH into EC2 and:
   - Pulls latest code from GitHub
   - Installs/upgrades dependencies
   - Clears Streamlit cache
   - Restarts the application
   - Verifies application is running

### Manual Deployment:

You can also trigger deployment manually:
- Go to **Actions** tab in GitHub
- Select **CI/CD Pipeline - Deploy to EC2**
- Click **Run workflow**

---

## 📊 Monitoring & Troubleshooting

### Check Application Status on EC2:

```bash
# SSH into EC2
ssh ubuntu@3.110.44.41

# Check if Streamlit is running
ps aux | grep streamlit

# Check application logs
tail -f /home/ubuntu/Optimization/dashboard.log

# Check systemd service (if using)
sudo systemctl status optimization-app
sudo journalctl -u optimization-app -f
```

### Check Nginx Status:

```bash
sudo systemctl status nginx
sudo tail -f /var/log/nginx/error.log
```

### Restart Services Manually:

```bash
# Restart Streamlit
sudo systemctl restart optimization-app
# Or kill and restart manually:
pkill -f "streamlit run src/dashboard.py"
cd /home/ubuntu/Optimization
nohup python3 -m streamlit run src/dashboard.py --server.port 8501 --server.address 0.0.0.0 > dashboard.log 2>&1 &

# Restart Nginx
sudo systemctl restart nginx
```

### Common Issues:

#### ❌ Deployment fails with "Permission denied"
- **Solution**: Ensure SSH key has correct permissions and is added to GitHub secrets correctly

#### ❌ Application not starting
- **Solution**: Check logs, verify Python dependencies are installed, check port 8501 is not in use

#### ❌ Cannot access dashboard
- **Solution**: 
  - Check EC2 security group allows inbound traffic on port 8501 (or 80 if using nginx)
  - Verify Streamlit is running: `ps aux | grep streamlit`
  - Check firewall: `sudo ufw status`

#### ❌ Git push fails
- **Solution**: Ensure git user email is configured: `git config user.email "infofitsoftware@gmail.com"`

---

## 🔒 Security Best Practices

1. **Never commit** `.env` files or AWS credentials
2. **Use IAM roles** on EC2 instead of hardcoded credentials when possible
3. **Restrict SSH access** to specific IPs in security groups
4. **Keep dependencies updated** for security patches
5. **Use HTTPS** with SSL certificates for production (recommended)

---

## 📝 Environment Variables

If your application needs environment variables on EC2:

1. Create `.env` file on EC2:
   ```bash
   ssh ubuntu@3.110.44.41
   cd /home/ubuntu/Optimization
   nano .env
   ```

2. Add your variables:
   ```env
   AWS_ACCESS_KEY_ID=your_key
   AWS_SECRET_ACCESS_KEY=your_secret
   AWS_REGION=us-east-2
   ```

3. The `.env` file is in `.gitignore` and won't be overwritten by deployments

---

## 🎯 Quick Reference

### GitHub Repository:
- **URL**: https://github.com/infofitsoftwaresolution/Optimization
- **Branch**: `main` (triggers auto-deployment)

### EC2 Instance:
- **IP**: 3.110.44.41
- **User**: ubuntu
- **Project Directory**: `/home/ubuntu/Optimization`
- **Dashboard URL**: http://3.110.44.41:8501

### Git Configuration:
- **Email**: infofitsoftware@gmail.com
- **Name**: InfoFit Software

---

## ✅ Deployment Checklist

- [ ] EC2 instance is running and accessible
- [ ] Initial setup script has been run on EC2
- [ ] GitHub secrets are configured (EC2_HOST, EC2_USER, SSH_PRIVATE_KEY)
- [ ] Git user email is configured locally
- [ ] Test deployment has been run successfully
- [ ] Dashboard is accessible at http://3.110.44.41:8501
- [ ] Nginx is configured (if using reverse proxy)

---

**🎉 You're all set! Every push to main will automatically deploy to EC2.**

