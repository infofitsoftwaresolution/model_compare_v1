"""Bedrock client factory (scaffold)."""

import boto3
from botocore.config import Config
from typing import Optional
import os
import sys
from pathlib import Path

# Add parent directory to path to import config
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def get_bedrock_client(region_name: Optional[str] = None):
    """
    Get Bedrock client using credentials from config.py if available,
    otherwise fall back to default AWS credentials.
    """
    cfg = Config(retries={"max_attempts": 3, "mode": "standard"}, read_timeout=60)
    
    # Try to import config to get explicit credentials
    try:
        from config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, AWS_PROFILE
        
        # Use explicit credentials if available
        if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
            session = boto3.Session(
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=region_name or AWS_REGION
            )
            return session.client("bedrock-runtime", config=cfg)
        
        # Use AWS profile if specified
        if AWS_PROFILE:
            session = boto3.Session(
                profile_name=AWS_PROFILE,
                region_name=region_name or AWS_REGION
            )
            return session.client("bedrock-runtime", config=cfg)
    except (ImportError, AttributeError):
        # If config.py doesn't exist or doesn't have these variables, fall back to defaults
        pass
    
    # Fall back to default AWS credentials (environment variables, ~/.aws/credentials, IAM role)
    if region_name:
        return boto3.client("bedrock-runtime", region_name=region_name, config=cfg)
    return boto3.client("bedrock-runtime", config=cfg)


