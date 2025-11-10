"""Extract prompts from Bedrock CloudTrail JSON log file and save to CSV."""

import json
import pandas as pd
from pathlib import Path
from typing import List, Dict
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.utils.json_utils import load_json_safe, validate_json_file


def extract_prompts_from_jsonl(jsonl_path: str | Path) -> List[Dict]:
    """Extract prompts from JSONL file (one JSON object per line)."""
    prompts = []
    jsonl_path = Path(jsonl_path)
    
    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSON file not found: {jsonl_path}")
    
    # Validate file first
    is_valid, validation_results = validate_json_file(jsonl_path)
    if not is_valid:
        raise ValueError(f"Invalid JSON file: {validation_results['summary']}")
    
    # Use safe JSON loader
    success, records, error = load_json_safe(jsonl_path)
    if not success:
        raise ValueError(f"Error loading JSON file: {error}")
    
    # Handle both JSON and JSONL formats
    if isinstance(records, list):
        # JSONL format - list of records
        records_list = records
    else:
        # Single JSON object - wrap in list
        records_list = [records]
    
    prompt_id = 1
    seen_prompts = set()  # Deduplicate
    
    for line_num, record in enumerate(records_list, 1):
        try:
            # Extract ALL user messages and combine them into complete prompt
            input_body = record.get("input", {}).get("inputBodyJson", {})
            messages = input_body.get("messages", [])
            
            if not messages:
                continue
            
            # Combine all user messages into one complete prompt
            user_message_parts = []
            for msg in messages:
                if msg.get("role") != "user":
                    continue
                
                content = msg.get("content", [])
                if not content:
                    continue
                
                # Extract text from content items
                for item in content:
                    if isinstance(item, dict):
                        text = item.get("text")
                        if text:
                            user_message_parts.append(text)
                            break
                    elif isinstance(item, str):
                        user_message_parts.append(item)
                        break
            
            if not user_message_parts:
                continue
            
            # Combine all user messages with double newline separator
            text_content = "\n\n".join(user_message_parts)
            
            # Deduplicate based on prompt text hash
            prompt_hash = hash(text_content)
            if prompt_hash in seen_prompts:
                continue
            seen_prompts.add(prompt_hash)
            
            # Detect if JSON is expected (simple heuristic)
            expected_json = (
                "json" in text_content.lower() or
                "return the result in a json" in text_content.lower() or
                "formatted as follows:" in text_content.lower()
            )
            
            # Extract category if possible (e.g., from modelId or operation)
            category = "json-gen" if expected_json else "general"
            operation = record.get("operation", "")
            if operation:
                category = operation.lower()
            
            prompts.append({
                "prompt_id": prompt_id,
                "prompt": text_content,
                "expected_json": expected_json,
                "category": category
            })
            
            prompt_id += 1
            
        except (KeyError, TypeError, AttributeError) as e:
            print(f"Warning: Skipping record {line_num} - Error parsing structure: {e}")
            continue
        except Exception as e:
            print(f"Warning: Skipping record {line_num} - Error: {e}")
            continue
    
    return prompts


def save_prompts_to_csv(prompts: List[Dict], output_csv: str | Path) -> None:
    """Save prompts to CSV file."""
    if not prompts:
        print("No prompts extracted!")
        return
    
    df = pd.DataFrame(prompts)
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    df.to_csv(output_path, index=False, encoding="utf-8")
    print(f"✅ Extracted {len(prompts)} unique prompts to {output_path}")
    print(f"   - JSON-expected: {df['expected_json'].sum()}")
    print(f"   - General: {(~df['expected_json']).sum()}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Extract prompts from Bedrock CloudTrail JSON")
    parser.add_argument(
        "--input",
        default="data/20251001T000153731Z_e9c5e90710a8738a.json",
        help="Path to input JSON/JSONL file"
    )
    parser.add_argument(
        "--output",
        default="data/test_prompts.csv",
        help="Path to output CSV file"
    )
    
    args = parser.parse_args()
    
    print(f"Reading prompts from: {args.input}")
    prompts = extract_prompts_from_jsonl(args.input)
    save_prompts_to_csv(prompts, args.output)


if __name__ == "__main__":
    main()

