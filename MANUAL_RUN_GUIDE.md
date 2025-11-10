# 📖 Manual Run Guide - Step-by-Step Instructions

> **🎯 This is the PRIMARY setup guide for this project.**  
> If you just cloned this repository, **start here** and follow the steps in order.

This guide provides detailed step-by-step instructions for manually running the Model Evaluation Framework for AWS Bedrock LLMs. Follow these instructions sequentially to set up and run the project successfully.

---

## Prerequisites

Before starting, ensure you have:
- ✅ Python 3.8 or higher installed
- ✅ AWS account with Bedrock access
- ✅ Bedrock models enabled in your AWS account:
  - `us.anthropic.claude-3-7-sonnet-20250219-v1:0` (Claude 3.7 Sonnet)
  - `us.meta.llama3-2-11b-instruct-v1:0` (Llama 3.2 11B Instruct)
- ✅ AWS credentials (Access Key ID and Secret Access Key)

---

## Step 1: Navigate to Project Directory

Open your terminal/command prompt and navigate to the project directory:

```bash
cd D:\Optimization
```

Or if you're using a different path:
```bash
cd <your-project-path>
```

---

## Step 2: Create Python Virtual Environment

### For Windows PowerShell:
```powershell
python -m venv .venv
```

### For Windows CMD:
```cmd
python -m venv .venv
```

### For Linux/Mac:
```bash
python3 -m venv .venv
```

**Expected output:** A new `.venv` folder will be created in your project directory.

---

## Step 3: Activate Virtual Environment

### For Windows PowerShell:
```powershell
.venv\Scripts\Activate.ps1
```

**Note:** If you get an execution policy error, run this first:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### For Windows CMD:
```cmd
.venv\Scripts\activate.bat
```

### For Linux/Mac:
```bash
source .venv/bin/activate
```

**Expected output:** Your terminal prompt should show `(.venv)` at the beginning, indicating the virtual environment is active.

---

## Step 4: Install Required Dependencies

With the virtual environment activated, install all required packages:

```bash
pip install -r requirements.txt
```

**Expected output:** You'll see packages being downloaded and installed. This may take a few minutes.

**Verify installation:**
```bash
pip list
```

You should see packages like:
- boto3
- pandas
- streamlit
- plotly
- tiktoken
- tqdm
- python-dotenv

---

## Step 5: Configure AWS Credentials

You have three options to configure AWS credentials. Choose the method that works best for you:

### Option A: Using .env File (Recommended)

1. Create a new file named `.env` in the project root directory:

   **Windows PowerShell:**
   ```powershell
   New-Item -Path .env -ItemType File
   ```

   **Windows CMD:**
   ```cmd
   type nul > .env
   ```

   **Linux/Mac:**
   ```bash
   touch .env
   ```

2. Open the `.env` file in a text editor and add your AWS credentials:

   ```
   AWS_ACCESS_KEY_ID=your_access_key_here
   AWS_SECRET_ACCESS_KEY=your_secret_key_here
   AWS_REGION=us-east-2
   ```

   **Replace:**
   - `your_access_key_here` with your actual AWS Access Key ID
   - `your_secret_key_here` with your actual AWS Secret Access Key
   - `us-east-2` with your AWS region if different

3. Save and close the file.

**⚠️ Important:** Never commit the `.env` file to version control!

### Option B: Using AWS CLI Profile

1. Configure AWS CLI (if not already done):
   ```bash
   aws configure
   ```

2. Enter your credentials when prompted:
   - AWS Access Key ID
   - AWS Secret Access Key
   - Default region name (e.g., `us-east-2`)
   - Default output format (press Enter for default)

### Option C: Using Environment Variables

**Windows PowerShell:**
```powershell
$env:AWS_ACCESS_KEY_ID="your_access_key_here"
$env:AWS_SECRET_ACCESS_KEY="your_secret_key_here"
$env:AWS_REGION="us-east-2"
```

**Windows CMD:**
```cmd
set AWS_ACCESS_KEY_ID=your_access_key_here
set AWS_SECRET_ACCESS_KEY=your_secret_key_here
set AWS_REGION=us-east-2
```

**Linux/Mac:**
```bash
export AWS_ACCESS_KEY_ID="your_access_key_here"
export AWS_SECRET_ACCESS_KEY="your_secret_key_here"
export AWS_REGION="us-east-2"
```

---

## Step 6: Verify AWS Bedrock Models Are Enabled

1. Log in to your AWS Console
2. Navigate to **Amazon Bedrock** → **Foundation models**
3. Verify these models are available and enabled:
   - Claude 3.7 Sonnet
   - Llama 3.2 11B Instruct

If models are not enabled, click "Request model access" for each model.

---

## Step 7: Prepare Test Prompts

You need a CSV file with test prompts. You have two options:

### Option A: Use Existing Prompts File

If you already have `data/test_prompts.csv` or `prompts_from_json.csv`, skip to Step 8.

### Option B: Extract Prompts from JSON Logs

If you have Bedrock CloudTrail JSON logs:

1. Place your JSON log file in the `data/` directory (e.g., `data/my_logs.json`)

2. Run the extraction script:
   ```bash
   python scripts/extract_prompts_from_json.py --input data/my_logs.json --output data/test_prompts.csv
   ```

3. Verify the output:
   ```bash
   # Windows PowerShell
   Get-Content data/test_prompts.csv -Head 5
   
   # Linux/Mac
   head -5 data/test_prompts.csv
   ```

**Expected CSV format:**
```csv
prompt_id,prompt,expected_json,category
1,"Your complete prompt text here...",True,converse
2,"Another prompt...",False,general
```

---

## Step 8: Verify Model Configuration

Check that `configs/models.yaml` is correctly configured:

```bash
# Windows PowerShell
Get-Content configs/models.yaml

# Linux/Mac
cat configs/models.yaml
```

The file should contain:
- Correct region name
- Two models: Claude 3.7 Sonnet and Llama 3.2 11B Instruct
- Valid model IDs matching your AWS account
- Pricing information

If you need to edit it, open `configs/models.yaml` in a text editor and modify as needed.

---

## Step 9: Run a Test Evaluation (Recommended First Step)

Before running a full evaluation, test with a small number of prompts:

```bash
python scripts/run_evaluation.py --models all --limit 3
```

**What this does:**
- Evaluates all configured models
- Uses only the first 3 prompts from your CSV file
- Tests the connection and configuration

**Expected output:**
```
✅ Found 2 model(s): ['Claude 3.7 Sonnet', 'Llama 3.2 11B Instruct']
✅ Loaded 3 prompt(s)
🏃 Run ID: run_20250101_120000
🚀 Starting evaluation...
   Models: 2
   Prompts: 3
   Total evaluations: 6

Evaluating: 100%|████████████| 6/6 [00:30<00:00,  5.0s/eval]

✅ Evaluation complete! Collected 6 metric records
💾 Saving metrics...
   Saved to: data/runs/raw_metrics.csv
📊 Generating aggregated report...
   Saved to: data/runs/model_comparison.csv
```

**If you see errors:**
- Check AWS credentials (Step 5)
- Verify models are enabled (Step 6)
- Check model IDs in `configs/models.yaml`

---

## Step 10: Run Full Evaluation

Once the test run is successful, run the full evaluation:

```bash
python scripts/run_evaluation.py --models all
```

**Or specify custom paths:**
```bash
python scripts/run_evaluation.py --models all --prompts data/test_prompts.csv --out data/runs
```

**What this does:**
- Evaluates all configured models on all prompts
- Measures latency, token usage, cost, and JSON validity
- Saves results to CSV files

**Expected duration:** Depends on number of prompts (typically 2-5 seconds per evaluation)

**Progress indicators:**
- Progress bar showing completion percentage
- Success (✅) or Error (❌) indicators for each evaluation
- Final summary with metrics

---

## Step 11: Verify Results Files

After evaluation completes, verify that results were generated:

```bash
# Windows PowerShell
Get-ChildItem data/runs

# Linux/Mac
ls -la data/runs
```

**Expected files:**
- `raw_metrics.csv` - Detailed per-request metrics
- `model_comparison.csv` - Aggregated comparison table

**View the results:**
```bash
# Windows PowerShell
Get-Content data/runs/model_comparison.csv

# Linux/Mac
cat data/runs/model_comparison.csv
```

---

## Step 12: Launch the Dashboard

View your results in an interactive dashboard:

1. **Activate your virtual environment** (if not already activated):
   ```powershell
   .venv\Scripts\Activate.ps1
   ```

2. Start the Streamlit dashboard:
   ```bash
   streamlit run src/dashboard.py
   ```

3. The dashboard will automatically open in your browser at:
   ```
   http://localhost:8501
   ```

   If it doesn't open automatically, copy the URL from the terminal output and paste it into your browser.

**Note:** On first run, Streamlit may ask for your email. You can skip this, or the project includes a `.streamlit/config.toml` file that prevents this prompt.

**Expected output in terminal:**
```
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
Network URL: http://192.168.x.x:8501
```

---

## Step 13: Explore Dashboard Results

In the dashboard, you can:

1. **View Summary Cards:**
   - Total evaluations
   - Success rate
   - Total cost
   - Models compared

2. **Check Model Comparison Table:**
   - Aggregated metrics per model
   - Latency (p50/p95/p99)
   - Average tokens and costs

3. **Explore Visualizations:**
   - Click on different tabs: **Latency**, **Tokens**, **Cost**, **JSON Validity**
   - View charts and graphs comparing models

4. **Filter Results:**
   - Use sidebar to select specific models
   - Filter by prompt IDs
   - Filter by status (success/error)

5. **Export Data:**
   - Click download buttons to export filtered results as CSV

---

## Step 14: Stop the Dashboard

When you're done viewing results:

1. Return to your terminal
2. Press `Ctrl + C` to stop the Streamlit server

---

## Common Commands Reference

### Run Evaluation with Different Options

```bash
# Test with limited prompts
python scripts/run_evaluation.py --models all --limit 5

# Evaluate specific models only
python scripts/run_evaluation.py --models "Claude 3.7 Sonnet"

# Custom output directory
python scripts/run_evaluation.py --models all --out data/my_results

# Custom run ID
python scripts/run_evaluation.py --models all --run-id my_test_run

# Skip report generation (faster for testing)
python scripts/run_evaluation.py --models all --limit 5 --skip-report
```

### View Results

```bash
# View raw metrics
# Windows PowerShell
Get-Content data/runs/raw_metrics.csv

# Linux/Mac
cat data/runs/raw_metrics.csv

# View comparison report
# Windows PowerShell
Get-Content data/runs/model_comparison.csv

# Linux/Mac
cat data/runs/model_comparison.csv
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError"
**Solution:** Make sure virtual environment is activated and dependencies are installed:
```bash
.venv\Scripts\Activate.ps1  # Windows PowerShell
pip install -r requirements.txt
```

### Issue: "NoCredentialsError" or "Unable to locate credentials"
**Solution:** Configure AWS credentials (see Step 5). Verify with:
```bash
aws sts get-caller-identity
```

### Issue: "ValidationException" or "AccessDeniedException"
**Solution:** 
- Check that model IDs in `configs/models.yaml` match your AWS account
- Verify models are enabled in AWS Bedrock console
- Ensure your AWS credentials have Bedrock permissions

### Issue: Dashboard shows "No data found"
**Solution:** 
- Run evaluation first (Step 9 or 10)
- Check file paths in dashboard sidebar
- Verify files exist in `data/runs/` directory

### Issue: Evaluation is very slow
**Solution:**
- Use `--limit` flag to test with fewer prompts first
- Check your internet connection
- Verify Bedrock model availability in your region

### Issue: Virtual environment activation fails
**Windows PowerShell execution policy error:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## Next Steps

After successfully running evaluations:

1. **Compare Results:** Use the dashboard to compare model performance
2. **Analyze Metrics:** Focus on latency, cost, and JSON validity
3. **Run Multiple Evaluations:** Test with different configurations
4. **Export Data:** Download results for further analysis

---

## Quick Checklist

Use this checklist to ensure you've completed all steps:

- [ ] Python virtual environment created and activated
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] AWS credentials configured
- [ ] Bedrock models enabled in AWS account
- [ ] Test prompts CSV file prepared
- [ ] Model configuration verified (`configs/models.yaml`)
- [ ] Test evaluation completed successfully
- [ ] Full evaluation run
- [ ] Results files verified
- [ ] Dashboard launched and viewed

---

**Need Help?** Refer to the main `README.md` file for additional information and troubleshooting tips.

---

**Happy Evaluating! 🎉**

