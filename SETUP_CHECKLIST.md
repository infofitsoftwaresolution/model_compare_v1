# ✅ Setup Checklist for New Clones

Use this checklist to ensure everything is set up correctly after cloning the repository.

## 📋 Pre-Flight Checklist

After cloning, verify these files exist:

- [ ] `requirements.txt` - Python dependencies
- [ ] `configs/models.yaml` - Model configurations
- [ ] `.env.example` - Example environment file (template)
- [ ] `setup.py` - Setup script
- [ ] `README.md` - Main documentation
- [ ] `QUICK_START.md` - Quick start guide
- [ ] `start_dashboard.bat` - Windows startup script
- [ ] `start_dashboard.sh` - Linux/Mac startup script

## 🚀 Setup Steps

### 1. Run Setup Script
```bash
python setup.py
```

**Expected output:**
- ✅ Created directories: `data/runs`, `data/cache`
- ✅ Found/created `.gitkeep` files
- ✅ Python version check
- ✅ Configuration check

### 2. Create Virtual Environment
```bash
# Windows
python -m venv .venv
.venv\Scripts\Activate.ps1

# Linux/Mac
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

**Verify installation:**
```bash
pip list | grep streamlit
pip list | grep boto3
```

### 4. Configure AWS Credentials

**Create `.env` file:**
```bash
# Windows PowerShell
Copy-Item .env.example .env

# Linux/Mac
cp .env.example .env
```

**Edit `.env` and add your credentials:**
```env
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-2
```

### 5. Verify Configuration

**Check models.yaml:**
```bash
# Windows PowerShell
Get-Content configs/models.yaml

# Linux/Mac
cat configs/models.yaml
```

Should show at least one model configuration.

### 6. Test Dashboard Startup

**Using startup script:**
```bash
# Windows
start_dashboard.bat

# Linux/Mac
chmod +x start_dashboard.sh
./start_dashboard.sh
```

**Or manually:**
```bash
streamlit run src/dashboard.py
```

**Expected:**
- Dashboard opens at `http://localhost:8501`
- No error messages in terminal
- Dashboard shows "No data found" (normal for fresh setup)

## 🐛 Common Issues

### Issue: "ModuleNotFoundError"
**Solution:** 
- Activate virtual environment
- Run `pip install -r requirements.txt`

### Issue: "NoCredentialsError"
**Solution:**
- Create `.env` file from `.env.example`
- Add AWS credentials
- Or configure AWS CLI: `aws configure`

### Issue: "FileNotFoundError: configs/models.yaml"
**Solution:**
- Verify `configs/models.yaml` exists
- Check file path is correct

### Issue: Dashboard shows "No data found"
**Status:** ✅ **This is normal!**
- Fresh installations have no data
- Upload CloudWatch logs or add prompts to get started

### Issue: Port 8501 already in use
**Solution:**
```bash
streamlit run src/dashboard.py --server.port 8502
```

## ✅ Final Verification

After setup, you should be able to:

- [ ] Run `python setup.py` without errors
- [ ] Activate virtual environment
- [ ] Import key modules: `python -c "import streamlit; import boto3"`
- [ ] Start dashboard: `streamlit run src/dashboard.py`
- [ ] Access dashboard at `http://localhost:8501`
- [ ] See dashboard UI (even if no data)

## 📚 Next Steps

Once setup is complete:

1. **Upload CloudWatch logs** via dashboard
2. **Select prompts** from CloudWatch logs
3. **Run evaluations** with your models
4. **View analytics** and compare models

## 🆘 Need Help?

- **Quick Start:** See [QUICK_START.md](QUICK_START.md)
- **Detailed Guide:** See [MANUAL_RUN_GUIDE.md](MANUAL_RUN_GUIDE.md)
- **Troubleshooting:** See README.md troubleshooting section

