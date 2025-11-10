# 🚀 Automatic Deployment Guide

Your CI/CD pipeline is **already configured** to automatically deploy whenever you push to the `main` branch!

## ✅ How It Works

1. **You push code to GitHub** → `git push origin main`
2. **GitHub Actions automatically triggers** → Runs tests
3. **If tests pass** → Automatically deploys to EC2
4. **EC2 updates** → Pulls latest code, restarts Streamlit
5. **Website updates** → Your changes appear at http://3.111.36.145:8501

## 📋 Current Configuration

- **Trigger:** Every push to `main` branch
- **Test Job:** Runs automatically on every push
- **Deploy Job:** Runs automatically if tests pass (only on push, not PRs)
- **Deployment Target:** EC2 instance at 3.111.36.145

## 🎯 How to Deploy Updates

### Step 1: Make Your Changes
Edit any files in your project (dashboard, configs, etc.)

### Step 2: Commit Your Changes
```bash
git add .
git commit -m "Your update description"
```

### Step 3: Push to Main
```bash
git push origin main
```

### Step 4: Watch It Deploy!
1. Go to: https://github.com/infofitsoftwaresolution/Optimization/actions
2. You'll see a new workflow run starting
3. Wait 1-2 minutes for deployment to complete
4. Your website will automatically update!

## 📊 Monitor Deployments

**GitHub Actions Dashboard:**
- https://github.com/infofitsoftwaresolution/Optimization/actions

**What to Look For:**
- ✅ Green checkmark = Deployment successful
- ❌ Red X = Deployment failed (check logs)

## 🔍 Verify Deployment

After pushing, you can verify on EC2:

```bash
# SSH into EC2
ssh ec2-user@3.111.36.145

# Check if latest code is pulled
cd /home/ec2-user/Optimization
git log -1

# Check if Streamlit is running
./scripts/health-check.sh

# View deployment logs
tail -f dashboard.log
```

## ⚙️ What Happens During Deployment

1. **Tests Run** (in GitHub Actions)
   - Installs dependencies
   - Runs basic import checks

2. **Code Deployment** (on EC2)
   - Pulls latest code from GitHub
   - Installs/updates Python dependencies
   - Stops existing Streamlit process
   - Starts new Streamlit process with latest code
   - Verifies app is running

3. **Website Updates**
   - Changes appear at http://3.111.36.145:8501
   - Usually within 1-2 minutes of push

## 🧪 Test It Now!

Make a small test change:

```bash
# On your local machine
echo "# Test update - $(date)" >> README.md
git add README.md
git commit -m "Test: Automatic deployment"
git push origin main
```

Then watch it deploy at: https://github.com/infofitsoftwaresolution/Optimization/actions

## ✅ Prerequisites (Already Set Up)

- ✅ GitHub Secrets configured:
  - `EC2_HOST` = 3.111.36.145
  - `EC2_USER` = ec2-user
  - `SSH_PRIVATE_KEY` = Your EC2 SSH key

- ✅ GitHub Actions workflow configured
- ✅ EC2 instance accessible
- ✅ Streamlit running on EC2

## 🐛 Troubleshooting

**If deployment fails:**

1. Check GitHub Actions logs:
   - Go to Actions tab
   - Click on the failed workflow
   - Check the "Deploy to EC2" step logs

2. Check EC2 manually:
   ```bash
   ssh ec2-user@3.111.36.145
   cd /home/ec2-user/Optimization
   ./scripts/health-check.sh
   tail -50 dashboard.log
   ```

3. Common issues:
   - **SSH connection failed** → Check GitHub Secrets
   - **Streamlit won't start** → Check logs on EC2
   - **Tests failing** → Check test output in GitHub Actions

## 🎉 You're All Set!

Your automatic deployment is **already working**! Just push to main and watch it deploy automatically.

**No manual steps needed** - it's fully automated! 🚀

