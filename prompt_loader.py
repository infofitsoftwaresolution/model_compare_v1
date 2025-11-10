"""
Prompt loader module - supports loading prompts from local files or S3.
"""

import boto3
import csv
import json
import os
from typing import List, Dict, Any
from config import PROMPT_SETTINGS, AWS_PROFILE, AWS_REGION, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY


class PromptLoader:
    """Load test prompts from local files or S3."""
    
    def __init__(self, source_type: str = "auto"):
        """
        Initialize prompt loader.
        
        Args:
            source_type: 'local', 's3', or 'auto' (detects based on config)
        """
        self.source_type = source_type
        self.s3_client = None
        
        if source_type in ("s3", "auto"):
            if PROMPT_SETTINGS.get("s3_bucket"):
                if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
                    session = boto3.Session(
                        aws_access_key_id=AWS_ACCESS_KEY_ID,
                        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                        region_name=AWS_REGION
                    )
                else:
                    session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
                self.s3_client = session.client("s3")
    
    def load_prompts(self, max_prompts: int = None) -> List[Dict[str, Any]]:
        """
        Load prompts from configured source.
        
        Args:
            max_prompts: Optional limit on number of prompts to load
            
        Returns:
            List of prompt dictionaries with 'prompt' key and optional metadata
        """
        # Determine source
        if self.source_type == "auto":
            if PROMPT_SETTINGS.get("s3_bucket"):
                source = "s3"
            elif PROMPT_SETTINGS.get("local_path"):
                source = "local"
            else:
                raise ValueError("No prompt source configured. Set PROMPT_SETTINGS['s3_bucket'] or ['local_path']")
        else:
            source = self.source_type
        
        # Load based on source type
        if source == "s3":
            return self._load_from_s3(max_prompts)
        elif source == "local":
            return self._load_from_local(max_prompts)
        else:
            raise ValueError(f"Unknown source type: {source}")
    
    def _load_from_local(self, max_prompts: int = None) -> List[Dict[str, Any]]:
        """Load prompts from local CSV or JSON file."""
        local_path = PROMPT_SETTINGS.get("local_path")
        if not local_path:
            raise ValueError("PROMPT_SETTINGS['local_path'] not set")
        
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Prompt file not found: {local_path}")
        
        prompts = []
        
        # Determine file type
        if local_path.endswith('.csv'):
            prompts = self._load_from_csv(local_path, max_prompts)
        elif local_path.endswith('.json'):
            prompts = self._load_from_json(local_path, max_prompts)
        elif local_path.endswith('.txt'):
            prompts = self._load_from_txt(local_path, max_prompts)
        else:
            raise ValueError(f"Unsupported file type. Use .csv, .json, or .txt")
        
        return prompts
    
    def _load_from_csv(self, filepath: str, max_prompts: int = None) -> List[Dict[str, Any]]:
        """Load prompts from CSV file."""
        prompts = []
        column = PROMPT_SETTINGS.get("csv_column", "prompt")
        
        with open(filepath, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            for idx, row in enumerate(reader, start=1):
                if max_prompts and idx > max_prompts:
                    break
                
                prompt_text = row.get(column) or row.get(column.capitalize()) or row.get(column.upper())
                if not prompt_text:
                    # Try common variations
                    prompt_text = row.get("Prompt") or row.get("PROMPT") or ""
                
                if prompt_text:
                    prompts.append({
                        "index": idx,
                        "prompt": prompt_text,
                        "metadata": {k: v for k, v in row.items() if k != column}
                    })
        
        return prompts
    
    def _load_from_json(self, filepath: str, max_prompts: int = None) -> List[Dict[str, Any]]:
        """Load prompts from JSON file (array, object with prompts array, or NDJSON)."""
        prompts = []
        
        # Try reading as NDJSON first (newline-delimited JSON)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                # Try to read first line to detect format
                first_line = f.readline().strip()
                if first_line:
                    # Check if it's valid JSON on first line
                    try:
                        json.loads(first_line)
                        # It's NDJSON format
                        f.seek(0)
                        idx = 1
                        for line in f:
                            if max_prompts and idx > max_prompts:
                                break
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                item = json.loads(line)
                                prompt_text, metadata = self._extract_prompt_from_dict(item)
                                if prompt_text:
                                    prompts.append({
                                        "index": idx,
                                        "prompt": prompt_text,
                                        "metadata": metadata
                                    })
                                    idx += 1
                            except json.JSONDecodeError:
                                continue
                        if prompts:
                            return prompts
                    except json.JSONDecodeError:
                        pass
        except Exception:
            pass
        
        # Try standard JSON format
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Handle array of prompts
        if isinstance(data, list):
            prompt_list = data
        # Handle object with prompts key
        elif isinstance(data, dict) and "prompts" in data:
            prompt_list = data["prompts"]
        else:
            # Try to extract from single object (like Bedrock log format)
            prompt_text, metadata = self._extract_prompt_from_dict(data)
            if prompt_text:
                return [{"index": 1, "prompt": prompt_text, "metadata": metadata}]
            raise ValueError("JSON must be an array, object with 'prompts' key, or NDJSON format")
        
        for idx, item in enumerate(prompt_list, start=1):
            if max_prompts and idx > max_prompts:
                break
            
            if isinstance(item, str):
                prompt_text = item
                metadata = {}
            elif isinstance(item, dict):
                prompt_text, metadata = self._extract_prompt_from_dict(item)
            else:
                continue
            
            if prompt_text:
                prompts.append({
                    "index": idx,
                    "prompt": prompt_text,
                    "metadata": metadata
                })
        
        return prompts
    
    def _extract_prompt_from_dict(self, item: Dict[str, Any]) -> tuple:
        """Extract prompt text from various dictionary structures."""
        # Standard prompt fields
        prompt_text = item.get("prompt") or item.get("text") or ""
        if prompt_text:
            metadata = {k: v for k, v in item.items() if k not in ("prompt", "text")}
            return prompt_text, metadata
        
        # Bedrock log format: input.inputBodyJson.messages[].content[].text
        # Combine ALL messages into a single prompt (important for conversation history)
        if "input" in item and isinstance(item["input"], dict):
            input_data = item["input"]
            if "inputBodyJson" in input_data and isinstance(input_data["inputBodyJson"], dict):
                body_json = input_data["inputBodyJson"]
                if "messages" in body_json and isinstance(body_json["messages"], list):
                    messages = body_json["messages"]
                    if messages:
                        # Combine all messages into a single prompt
                        message_texts = []
                        for msg in messages:
                            if isinstance(msg, dict) and "content" in msg:
                                content = msg["content"]
                                if isinstance(content, list):
                                    # Extract all text content from this message
                                    for content_item in content:
                                        if isinstance(content_item, dict) and "text" in content_item:
                                            message_texts.append(content_item["text"])
                        
                        if message_texts:
                            # Combine messages with newlines (preserving conversation flow)
                            prompt_text = "\n\n".join(message_texts)
                            # Extract metadata from top level
                            metadata = {
                                k: v for k, v in item.items() 
                                if k not in ("input", "timestamp")
                            }
                            metadata["timestamp"] = item.get("timestamp")
                            metadata["modelId"] = item.get("modelId")
                            metadata["requestId"] = item.get("requestId")
                            metadata["message_count"] = len(messages)  # Track how many messages were combined
                            return prompt_text, metadata
        
        # Empty result
        return "", {k: v for k, v in item.items()}
    
    def _load_from_txt(self, filepath: str, max_prompts: int = None) -> List[Dict[str, Any]]:
        """Load prompts from text file (one prompt per line or separated by blank lines)."""
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by double newlines (blank lines) or single newlines
        raw_prompts = [p.strip() for p in content.split('\n\n') if p.strip()]
        if len(raw_prompts) == 1:
            # If no double newlines, try single newlines
            raw_prompts = [p.strip() for p in content.split('\n') if p.strip()]
        
        prompts = []
        for idx, prompt_text in enumerate(raw_prompts, start=1):
            if max_prompts and idx > max_prompts:
                break
            prompts.append({
                "index": idx,
                "prompt": prompt_text,
                "metadata": {}
            })
        
        return prompts
    
    def _load_from_s3(self, max_prompts: int = None) -> List[Dict[str, Any]]:
        """Load prompts from S3 bucket."""
        if not self.s3_client:
            raise ValueError("S3 client not initialized")
        
        bucket = PROMPT_SETTINGS.get("s3_bucket")
        key = PROMPT_SETTINGS.get("s3_key")
        
        if not bucket or not key:
            raise ValueError("PROMPT_SETTINGS['s3_bucket'] and ['s3_key'] must be set for S3 loading")
        
        # Download file from S3
        print(f"Downloading prompts from s3://{bucket}/{key}...")
        response = self.s3_client.get_object(Bucket=bucket, Key=key)
        content = response['Body'].read().decode('utf-8')
        
        # Create temporary file or parse directly
        if key.endswith('.csv'):
            # Parse CSV from string
            prompts = []
            column = PROMPT_SETTINGS.get("csv_column", "prompt")
            reader = csv.DictReader(content.splitlines())
            for idx, row in enumerate(reader, start=1):
                if max_prompts and idx > max_prompts:
                    break
                prompt_text = row.get(column) or row.get(column.capitalize()) or ""
                if prompt_text:
                    prompts.append({
                        "index": idx,
                        "prompt": prompt_text,
                        "metadata": {k: v for k, v in row.items() if k != column}
                    })
            return prompts
        elif key.endswith('.json'):
            # Parse JSON directly without temp file
            data = json.loads(content)
            
            prompts = []
            
            # Handle array of prompts
            if isinstance(data, list):
                prompt_list = data
            # Handle object with prompts key
            elif isinstance(data, dict) and "prompts" in data:
                prompt_list = data["prompts"]
            else:
                raise ValueError("JSON must be an array or object with 'prompts' key")
            
            for idx, item in enumerate(prompt_list, start=1):
                if max_prompts and idx > max_prompts:
                    break
                
                if isinstance(item, str):
                    prompt_text = item
                    metadata = {}
                elif isinstance(item, dict):
                    prompt_text = item.get("prompt") or item.get("text") or ""
                    metadata = {k: v for k, v in item.items() if k not in ("prompt", "text")}
                else:
                    continue
                
                if prompt_text:
                    prompts.append({
                        "index": idx,
                        "prompt": prompt_text,
                        "metadata": metadata
                    })
            
            return prompts
        else:
            raise ValueError(f"Unsupported S3 file type: {key}")

