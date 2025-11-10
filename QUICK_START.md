# 🚀 Quick Start Guide

Get the dashboard running in 5 minutes!

## Prerequisites

- Python 3.8 or higher
- AWS account with Bedrock access
- AWS credentials (Access Key ID and Secret Access Key)

## Step 1: Clone the Repository

```bash
git clone <your-repository-url>
cd Optimization
```

## Step 2: Set Up Python Environment

**Windows PowerShell:**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Windows CMD:**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

## Step 4: Run Setup Script (Optional but Recommended)

```bash
python setup.py
```

This will:
- Create necessary directories
- Check your configuration
- Verify Python version

## Step 5: Configure AWS Credentials

**Option A: Using .env file (Recommended)**

1. Copy the example file:
   ```bash
   # Windows PowerShell
   Copy-Item .env.example .env
   
   # Linux/Mac
   cp .env.example .env
   ```

2. Edit `.env` and add your credentials:
   ```env
   AWS_ACCESS_KEY_ID=your_access_key_here
   AWS_SECRET_ACCESS_KEY=your_secret_key_here
   AWS_REGION=us-east-2
   ```

**Option B: Using AWS CLI**

```bash
aws configure
```

## Step 6: Start the Dashboard

**Option A: Using Startup Script (Easiest)**

**Windows:**
```bash
start_dashboard.bat
```

**Linux/Mac:**
```bash
chmod +x start_dashboard.sh
./start_dashboard.sh
```

**Option B: Manual Start**

Make sure your virtual environment is activated, then:
```bash
streamlit run src/dashboard.py
```

The dashboard will open automatically in your browser at `http://localhost:8501`

## ✅ You're Done!

The dashboard is now running. You can:
- Upload CloudWatch logs
- Select prompts from logs
- Run evaluations
- View analytics

## 🐛 Troubleshooting

### "ModuleNotFoundError"
**Solution:** Make sure you activated the virtual environment and installed dependencies:
```bash
pip install -r requirements.txt
```

### "NoCredentialsError"
**Solution:** Configure AWS credentials (see Step 5)

### Dashboard shows "No data found"
**Solution:** This is normal for a fresh setup. You can:
- Upload CloudWatch logs to extract prompts
- Enter custom prompts in the sidebar
- Upload a CSV/JSON file with prompts

### Port 8501 already in use
**Solution:** Use a different port:
```bash
streamlit run src/dashboard.py --server.port 8502
```

## 📚 Need More Help?

- See [README.md](README.md) for detailed documentation
- See [MANUAL_RUN_GUIDE.md](MANUAL_RUN_GUIDE.md) for comprehensive setup instructions

