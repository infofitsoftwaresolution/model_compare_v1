"""JSON utilities: validation and safe parsing."""

import json
from pathlib import Path
from typing import Any, Tuple, List, Dict, Optional


def is_valid_json(text: str) -> Tuple[bool, Any]:
    """
    Validate if a string is valid JSON and return the parsed object.
    
    Args:
        text: JSON string to validate
        
    Returns:
        Tuple of (is_valid, parsed_object_or_error_message)
    """
    try:
        obj = json.loads(text)
        return True, obj
    except json.JSONDecodeError as e:
        return False, f"JSON decode error at line {e.lineno}, column {e.colno}: {e.msg}"
    except Exception as e:
        return False, str(e)


def detect_json_format(file_path: Path) -> str:
    """
    Detect if a file is JSON, JSONL, or invalid.
    
    Args:
        file_path: Path to the file to check
        
    Returns:
        'json', 'jsonl', or 'unknown'
    """
    if file_path.suffix == ".jsonl":
        return "jsonl"
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Try to parse as regular JSON first
        try:
            json.loads(content)
            return "json"
        except json.JSONDecodeError:
            # Might be JSONL - check if each line is valid JSON
            lines = content.strip().split('\n')
            if len(lines) > 1:
                valid_lines = 0
                for line in lines:
                    line = line.strip()
                    if line:
                        try:
                            json.loads(line)
                            valid_lines += 1
                        except json.JSONDecodeError:
                            pass
                
                # If more than 50% of non-empty lines are valid JSON, it's likely JSONL
                if valid_lines > len([l for l in lines if l.strip()]) * 0.5:
                    return "jsonl"
            
            return "unknown"
    except Exception:
        return "unknown"


def validate_json_file(file_path: Path) -> Tuple[bool, Dict[str, Any]]:
    """
    Validate a JSON or JSONL file and return detailed results.
    
    Args:
        file_path: Path to the JSON/JSONL file
        
    Returns:
        Tuple of (is_valid, results_dict)
        results_dict contains: format, line_count, error_count, errors, summary
    """
    results = {
        "format": "unknown",
        "line_count": 0,
        "error_count": 0,
        "errors": [],
        "summary": "",
        "valid": False
    }
    
    if not file_path.exists():
        results["errors"].append(f"File not found: {file_path}")
        results["summary"] = "File does not exist"
        return False, results
    
    format_type = detect_json_format(file_path)
    results["format"] = format_type
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if format_type == "jsonl" or (format_type == "unknown" and file_path.suffix == ".jsonl"):
                # Validate JSONL format - one JSON object per line
                line_num = 0
                for line in f:
                    line_num += 1
                    line = line.strip()
                    if not line:
                        continue
                    
                    results["line_count"] += 1
                    is_valid, parsed = is_valid_json(line)
                    if not is_valid:
                        results["error_count"] += 1
                        results["errors"].append(f"Line {line_num}: {parsed}")
                
                if results["error_count"] == 0:
                    results["valid"] = True
                    results["summary"] = f"Valid JSONL file with {results['line_count']} objects"
                else:
                    results["summary"] = f"Invalid JSONL file: {results['error_count']} errors found"
            
            else:
                # Validate regular JSON format
                content = f.read()
                is_valid, parsed = is_valid_json(content)
                
                if is_valid:
                    results["valid"] = True
                    if isinstance(parsed, dict):
                        results["summary"] = f"Valid JSON object with {len(parsed)} keys"
                        results["line_count"] = len(content.split('\n'))
                    elif isinstance(parsed, list):
                        results["summary"] = f"Valid JSON array with {len(parsed)} items"
                        results["line_count"] = len(content.split('\n'))
                    else:
                        results["summary"] = "Valid JSON"
                else:
                    results["error_count"] = 1
                    results["errors"].append(f"Invalid JSON: {parsed}")
                    results["summary"] = f"Invalid JSON: {parsed}"
    
    except UnicodeDecodeError as e:
        results["error_count"] = 1
        results["errors"].append(f"Encoding error: {str(e)}")
        results["summary"] = "File encoding error (not UTF-8)"
    except Exception as e:
        results["error_count"] = 1
        results["errors"].append(f"Error reading file: {str(e)}")
        results["summary"] = f"Error: {str(e)}"
    
    return results["valid"], results


def load_json_safe(file_path: Path) -> Tuple[bool, Any, Optional[str]]:
    """
    Safely load a JSON or JSONL file.
    
    Args:
        file_path: Path to the JSON/JSONL file
        
    Returns:
        Tuple of (success, data_or_none, error_message_or_none)
        For JSON files: data is the parsed object
        For JSONL files: data is a list of parsed objects
    """
    if not file_path.exists():
        return False, None, f"File not found: {file_path}"
    
    format_type = detect_json_format(file_path)
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            if format_type == "jsonl" or file_path.suffix == ".jsonl":
                # Load JSONL - return list of objects
                objects = []
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line:
                        continue
                    
                    is_valid, parsed = is_valid_json(line)
                    if not is_valid:
                        return False, None, f"Line {line_num}: {parsed}"
                    
                    objects.append(parsed)
                
                return True, objects, None
            else:
                # Load regular JSON
                content = f.read()
                is_valid, parsed = is_valid_json(content)
                if not is_valid:
                    return False, None, parsed
                
                return True, parsed, None
    
    except UnicodeDecodeError as e:
        return False, None, f"Encoding error: {str(e)}"
    except Exception as e:
        return False, None, f"Error reading file: {str(e)}"


