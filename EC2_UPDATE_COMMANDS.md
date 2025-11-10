# EC2 Update Commands

If you have local changes on EC2 and need to pull updates, use these commands:

## Option 1: Stash local changes (recommended)

```bash
cd /home/ec2-user/Optimization

# Stash any local changes
git stash

# Pull latest changes
git pull origin main

# If you need your stashed changes back:
# git stash pop
```

## Option 2: Discard local changes (if you don't need them)

```bash
cd /home/ec2-user/Optimization

# Discard local changes
git checkout -- scripts/health-check.sh scripts/verify-deployment.sh

# Pull latest changes
git pull origin main
```

## Option 3: Reset to match remote (nuclear option)

```bash
cd /home/ec2-user/Optimization

# Reset to match remote exactly
git fetch origin
git reset --hard origin/main
```

**⚠️ Warning:** Option 3 will discard ALL local changes. Only use if you're sure you don't need them.

