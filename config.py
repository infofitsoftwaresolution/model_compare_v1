"""
Configuration module for model evaluation framework.
Define models, pricing, and evaluation settings here.
"""

from typing import Dict, Any
import os

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    from pathlib import Path
    
    # Load .env file from project root
    env_path = Path(__file__).parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # python-dotenv not installed, skip loading .env file
    pass

# AWS Configuration
# Priority order for credentials:
# 1. Environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY) from .env file or system
# 2. AWS Profile (AWS_PROFILE)
# 3. Default AWS credentials (~/.aws/credentials or IAM role)

# AWS Region (required)
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")

# AWS Profile (optional - used if AWS_ACCESS_KEY_ID not set)
AWS_PROFILE = os.getenv("AWS_PROFILE", None)

# AWS Credentials (optional - set via environment variables or leave as None)
# Set these in your environment or .env file:
#   export AWS_ACCESS_KEY_ID=your_access_key_here
#   export AWS_SECRET_ACCESS_KEY=your_secret_key_here
# Or use AWS_PROFILE instead
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", None)
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", None)

# Model IDs for Bedrock
# Note: Primary configuration is in configs/models.yaml
# This is kept for backward compatibility
MODELS: Dict[str, Dict[str, Any]] = {
    "claude-sonnet": {
        "model_id": "us.anthropic.claude-3-7-sonnet-20250219-v1:0",
        "provider": "anthropic",
        "name": "Claude 3.7 Sonnet",
    },
    "llama-3-2-11b": {
        "model_id": "us.meta.llama3-2-11b-instruct-v1:0",
        "provider": "meta",
        "name": "Llama 3.2 11B Instruct",
    },
    "nova-pro": {
        "model_id": "us.amazon.nova-pro-v1:0",
        "provider": "amazon",
        "name": "Nova Pro",
    },
}

# Pricing per 1K tokens (input/output) in USD
# Source: AWS Bedrock pricing as of 2025
# Note: Primary pricing configuration is in configs/models.yaml
PRICING: Dict[str, Dict[str, float]] = {
    "claude-sonnet": {"input": 0.008, "output": 0.024},
    "llama-3-2-11b": {"input": 0.0006, "output": 0.0008},
    "nova-pro": {"input": 0.002, "output": 0.006},
}

# Evaluation Settings
EVAL_SETTINGS = {
    "max_tokens": 1500,
    "temperature": 0.7,
    "max_retries": 2,
    "json_retry_prompt_prefix": "Return ONLY valid JSON. No extra text.\n",
    # Enhanced prompt prefix for Llama models to encourage JSON output
    "llama_json_prompt_suffix": "\n\nIMPORTANT: Return ONLY valid JSON. No markdown formatting, no code blocks, no explanations. Just the raw JSON array or object.",
}

# Prompt Loading Settings
PROMPT_SETTINGS = {
    "local_path": "20251001T000153731Z_e9c5e90710a8738a.json",  # Default: included sample file
    "s3_bucket": None,   # Set to bucket name if using S3
    "s3_key": None,      # Set to S3 key/prefix if using S3
    "csv_column": "prompt",  # Column name in CSV containing prompts
}

