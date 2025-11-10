# Model Evaluation Framework for AWS Bedrock LLMs

A comprehensive framework to compare multiple AWS Bedrock LLMs using production-like prompts. Measure latency, token usage, JSON validity, and cost, then visualize results in an interactive Streamlit dashboard.

---

## Quick Start

**New to this project?** Choose your path:

- **[Quick Start Guide](QUICK_START.md)** - Get running in 5 minutes (recommended for experienced developers)
- **[Detailed Setup Guide](MANUAL_RUN_GUIDE.md)** - Step-by-step instructions with explanations
- **[Setup Checklist](SETUP_CHECKLIST.md)** - Verify your installation step-by-step

### First Steps After Cloning

```bash
# 1. Run setup script (creates directories and checks configuration)
python setup.py

# 2. Create virtual environment
python -m venv .venv

# 3. Activate virtual environment
# Windows:
.venv\Scripts\Activate.ps1
# Linux/Mac:
source .venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Configure AWS credentials (see below)

# 6. Start dashboard
streamlit run src/dashboard.py
```

---

## Features

- **Multi-model evaluation** - Test multiple Bedrock models with the same prompts
- **Comprehensive metrics** - Latency, token usage, JSON validity, and cost tracking
- **Interactive dashboard** - Visualize results with charts and comparisons
- **CloudWatch integration** - Upload and parse CloudWatch logs, extract prompts
- **Config-driven** - Manage models and pricing via YAML configuration
- **Export capabilities** - Download results as CSV for further analysis

---

## Configuration

### AWS Credentials

You have three options to configure AWS credentials:

**Option 1: Environment file (Recommended)**

1. Copy the example file:
   ```bash
   # Windows
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

**Option 2: AWS CLI Profile**

```bash
aws configure
```

**Option 3: Environment Variables**

```bash
export AWS_ACCESS_KEY_ID=your_access_key_here
export AWS_SECRET_ACCESS_KEY=your_secret_key_here
export AWS_REGION=us-east-2
```

### Model Configuration

Edit `configs/models.yaml` to configure your models:

```yaml
region_name: us-east-2

models:
  - name: Claude 3.7 Sonnet
    provider: anthropic
    bedrock_model_id: us.anthropic.claude-3-7-sonnet-20250219-v1:0
    tokenizer: anthropic
    pricing:
      input_per_1k_tokens_usd: 0.008
      output_per_1k_tokens_usd: 0.024
    generation_params:
      max_tokens: 1500
      temperature: 0.7
      top_p: 0.95
```

**Note:** Ensure the models are enabled in your AWS Bedrock account before running evaluations.

---

## Project Structure

```
Optimization/
├── src/                    # Source code
│   ├── dashboard.py        # Streamlit dashboard
│   ├── evaluator.py        # Model evaluation logic
│   ├── cloudwatch_parser.py # CloudWatch log parser
│   ├── model_registry.py   # Model configuration management
│   └── utils/              # Utility modules
├── configs/                # Configuration files
│   ├── models.yaml         # Model definitions and pricing
│   └── settings.yaml       # Application settings
├── data/                   # Data directory
│   ├── runs/               # Evaluation results (generated)
│   └── cache/              # Cache files
├── scripts/                # Utility scripts
│   ├── run_evaluation.py   # Run model evaluations
│   └── extract_prompts_from_json.py
├── setup.py                # Setup script
├── requirements.txt        # Python dependencies
└── README.md              # This file
```

---

## Usage

### Running Evaluations

**Test run (recommended first):**
```bash
python scripts/run_evaluation.py --models all --limit 3
```

**Full evaluation:**
```bash
python scripts/run_evaluation.py --models all
```

**Specific models:**
```bash
python scripts/run_evaluation.py --models "Claude 3.7 Sonnet,Llama 3.2 11B Instruct"
```

### Starting the Dashboard

**Using startup scripts:**
```bash
# Windows
start_dashboard.bat

# Linux/Mac
chmod +x start_dashboard.sh
./start_dashboard.sh
```

**Manual start:**
```bash
streamlit run src/dashboard.py
```

The dashboard will open at `http://localhost:8501`

### Dashboard Features

- Upload CloudWatch logs and extract prompts
- Select prompts from CloudWatch logs for evaluation
- Run evaluations directly from the dashboard
- View interactive visualizations
- Compare models side-by-side
- Export results as CSV

---

## CloudWatch Integration

The dashboard supports uploading CloudWatch log files:

1. Upload your CloudWatch log file (`.jsonl` format)
2. The parser extracts Bedrock API calls and metrics
3. Select prompts from the parsed logs
4. Use selected prompts to run evaluations

**Supported formats:**
- JSON Lines (`.jsonl`)
- JSON arrays
- CloudWatch log exports

---

## Troubleshooting

**ModuleNotFoundError**
```bash
# Make sure virtual environment is activated
pip install -r requirements.txt
```

**NoCredentialsError**
- Verify AWS credentials in `.env` file or AWS CLI configuration
- Check that credentials have Bedrock permissions

**ValidationException**
- Verify model IDs in `configs/models.yaml` match your AWS account
- Ensure models are enabled in AWS Bedrock console

**Dashboard shows "No data found"**
- This is normal for a fresh installation
- Run an evaluation or upload CloudWatch logs to get started

**Port 8501 already in use**
```bash
streamlit run src/dashboard.py --server.port 8502
```

For more detailed troubleshooting, see [MANUAL_RUN_GUIDE.md](MANUAL_RUN_GUIDE.md).

---

## Output Files

After running evaluations, you'll find:

- `data/runs/raw_metrics.csv` - Detailed per-request metrics
- `data/runs/model_comparison.csv` - Aggregated comparison by model

**Metrics tracked:**
- Input/output tokens
- Latency (p50, p95, p99)
- Cost per request
- JSON validity
- Success/error status

---

## Security

- Never commit `.env` file to version control
- Use AWS IAM roles with minimal required permissions
- Review AWS CloudTrail logs regularly
- Keep dependencies updated

---

## CI/CD Deployment

This project includes automated CI/CD deployment to EC2 using GitHub Actions.

**Before pushing:**
```bash
git config user.email "infofitsoftware@gmail.com"
git config user.name "InfoFit Software"
```

For deployment details, see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Additional Resources

- [AWS Bedrock Documentation](https://docs.aws.amazon.com/bedrock/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

---

## License

[Add your license here]

---

## Support

For detailed setup instructions and troubleshooting:
- [Quick Start Guide](QUICK_START.md)
- [Manual Run Guide](MANUAL_RUN_GUIDE.md)
- [Setup Checklist](SETUP_CHECKLIST.md)
