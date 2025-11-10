"""CloudWatch log parser for extracting Bedrock metrics."""

import json
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd


class CloudWatchParser:
    """Parse CloudWatch logs and extract Bedrock model metrics."""
    
    def __init__(self, model_registry=None):
        """
        Initialize CloudWatch parser.
        
        Args:
            model_registry: Optional ModelRegistry instance for model name mapping
        """
        self.model_registry = model_registry
    
    def parse_log_file(self, log_content: str) -> List[Dict[str, Any]]:
        """
        Parse CloudWatch log file content and extract metrics.
        
        Args:
            log_content: Content of CloudWatch log file (JSON lines or JSON array)
        
        Returns:
            List of metric dictionaries
        """
        metrics = []
        
        # Try to parse as JSON lines (one JSON object per line) - most common format
        lines = log_content.strip().split('\n')
        
        # If we have multiple lines, assume JSONL format
        if len(lines) > 1:
            for line_num, line in enumerate(lines, 1):
                if not line.strip():
                    continue
                
                try:
                    # Parse each line as JSON
                    log_entry = json.loads(line)
                    metric = self._extract_metrics_from_entry(log_entry, line_num)
                    if metric:
                        metrics.append(metric)
                except json.JSONDecodeError as e:
                    # Skip malformed lines
                    continue
        else:
            # Single line - try to parse as JSON array or single object
            try:
                # Try as JSON array first
                log_entries = json.loads(log_content)
                if isinstance(log_entries, list):
                    for line_num, entry in enumerate(log_entries, 1):
                        metric = self._extract_metrics_from_entry(entry, line_num)
                        if metric:
                            metrics.append(metric)
                elif isinstance(log_entries, dict):
                    # Single JSON object
                    metric = self._extract_metrics_from_entry(log_entries, 1)
                    if metric:
                        metrics.append(metric)
            except json.JSONDecodeError:
                # Try as single line JSONL
                try:
                    log_entry = json.loads(log_content)
                    metric = self._extract_metrics_from_entry(log_entry, 1)
                    if metric:
                        metrics.append(metric)
                except json.JSONDecodeError:
                    pass
        
        return metrics
    
    def _extract_metrics_from_entry(self, entry: Dict[str, Any], line_num: int) -> Optional[Dict[str, Any]]:
        """
        Extract metrics from a single CloudWatch log entry.
        
        Args:
            entry: CloudWatch log entry dictionary
            line_num: Line number for error tracking
        
        Returns:
            Metric dictionary or None if not a Bedrock invocation
        """
        # Handle CloudWatch log format with nested message field
        # If message is a JSON string, parse it and use that as the entry
        if "message" in entry and isinstance(entry["message"], str):
            try:
                parsed_message = json.loads(entry["message"])
                if isinstance(parsed_message, dict):
                    # Merge parsed message with entry (parsed message takes precedence)
                    entry = {**entry, **parsed_message}
            except (json.JSONDecodeError, TypeError):
                pass  # Keep original entry if parsing fails
        
        # Check if this is a Bedrock API call
        if not self._is_bedrock_entry(entry):
            return None
        
        try:
            # Extract basic information
            timestamp = self._extract_timestamp(entry)
            model_id = self._extract_model_id(entry)
            model_name = self._get_model_name(model_id)
            
            # Extract request/response data
            request_data = self._extract_request_data(entry)
            response_data = self._extract_response_data(entry)
            
            # Extract metrics
            input_tokens = self._extract_input_tokens(entry, request_data)
            output_tokens = self._extract_output_tokens(entry, response_data)
            latency_ms = self._extract_latency(entry)
            
            # Extract prompt and response
            prompt = self._extract_prompt(entry, request_data)
            response = self._extract_response(entry, response_data)
            
            # Calculate costs (if pricing available)
            cost_input, cost_output, cost_total = self._calculate_costs(
                model_id, input_tokens, output_tokens
            )
            
            # Validate JSON if response exists
            json_valid = None
            if response:
                try:
                    json.loads(response)
                    json_valid = True
                except (json.JSONDecodeError, TypeError):
                    # Try to extract JSON from markdown code blocks
                    json_match = re.search(r'```(?:json)?\s*(\{.*?\}|\[.*?\])\s*```', response, re.DOTALL)
                    if json_match:
                        try:
                            json.loads(json_match.group(1))
                            json_valid = True
                        except json.JSONDecodeError:
                            json_valid = False
                    else:
                        json_valid = False
            
            # Determine status
            status = "success" if response_data and not self._has_error(entry) else "error"
            error = None
            if status == "error":
                error = self._extract_error(entry)
            
            metric = {
                "timestamp": timestamp,
                "run_id": f"cloudwatch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "model_name": model_name,
                "model_id": model_id,
                "prompt_id": None,  # CloudWatch logs don't have prompt IDs
                "input_prompt": prompt,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "latency_ms": latency_ms,
                "json_valid": json_valid,
                "error": error,
                "status": status,
                "cost_usd_input": cost_input,
                "cost_usd_output": cost_output,
                "cost_usd_total": cost_total,
                "response": response,
                "source": "cloudwatch"  # Mark as CloudWatch source
            }
            
            return metric
            
        except Exception as e:
            # Log error but continue processing
            print(f"Error parsing log entry at line {line_num}: {e}")
            return None
    
    def _is_bedrock_entry(self, entry: Dict[str, Any]) -> bool:
        """Check if log entry is a Bedrock API call."""
        # Check for CloudWatch log format with nested message
        # Format: {"logStreamName": "aws/bedrock/...", "message": "{...}"}
        if "logStreamName" in entry:
            log_stream = str(entry.get("logStreamName", "")).lower()
            if "bedrock" in log_stream:
                return True
        
        # Check if message field contains Bedrock data (common in CloudWatch logs)
        if "message" in entry:
            message = entry["message"]
            # If message is a JSON string, parse it
            if isinstance(message, str):
                try:
                    parsed_message = json.loads(message)
                    if isinstance(parsed_message, dict):
                        # Check parsed message for Bedrock indicators
                        if "modelId" in parsed_message or "operation" in parsed_message:
                            operation = parsed_message.get("operation", "").lower()
                            if "converse" in operation or "invokemodel" in operation:
                                return True
                        if "bedrock" in str(parsed_message).lower():
                            return True
                except (json.JSONDecodeError, TypeError):
                    pass
            # Check message string directly
            elif isinstance(message, dict):
                if "modelId" in message or "operation" in message:
                    return True
        
        # Check various CloudWatch log formats
        event_name = entry.get("eventName", "")
        service = entry.get("eventSource", "")
        
        # Check for Bedrock service
        if "bedrock" in service.lower() or "bedrock" in str(entry).lower():
            return True
        
        # Check for InvokeModel or Converse API calls
        if "invokemodel" in event_name.lower() or "converse" in event_name.lower():
            return True
        
        # Check for Bedrock in request parameters
        if "requestParameters" in entry:
            params = entry["requestParameters"]
            if isinstance(params, dict):
                if "modelId" in params or "modelIdentifier" in params:
                    return True
        
        # Check for operation field (common in Bedrock logs)
        if "operation" in entry:
            operation = str(entry.get("operation", "")).lower()
            if "converse" in operation or "invokemodel" in operation:
                return True
        
        # Check for modelId field directly
        if "modelId" in entry:
            return True
        
        return False
    
    def _extract_timestamp(self, entry: Dict[str, Any]) -> str:
        """Extract timestamp from log entry."""
        # Try various timestamp fields
        for field in ["eventTime", "timestamp", "time", "@timestamp"]:
            if field in entry:
                ts = entry[field]
                if isinstance(ts, str):
                    return ts
                elif isinstance(ts, (int, float)):
                    # Convert Unix timestamp
                    return datetime.fromtimestamp(ts).isoformat() + "Z"
        
        # Default to current time
        return datetime.utcnow().isoformat() + "Z"
    
    def _extract_model_id(self, entry: Dict[str, Any]) -> str:
        """Extract model ID from log entry."""
        # Check direct modelId field (common in Bedrock logs)
        if "modelId" in entry:
            model_id = entry["modelId"]
            if model_id:
                return str(model_id)
        
        # Check requestParameters
        if "requestParameters" in entry:
            params = entry["requestParameters"]
            if isinstance(params, dict):
                model_id = params.get("modelId") or params.get("modelIdentifier") or params.get("model")
                if model_id:
                    return str(model_id)
        
        # Check responseElements
        if "responseElements" in entry:
            response = entry["responseElements"]
            if isinstance(response, dict):
                model_id = response.get("modelId") or response.get("modelIdentifier")
                if model_id:
                    return str(model_id)
        
        # Check in the entire entry structure using regex
        entry_str = json.dumps(entry)
        model_id_match = re.search(r'"modelId"\s*:\s*"([^"]+)"', entry_str)
        if model_id_match:
            return model_id_match.group(1)
        
        return "unknown"
    
    def _get_model_name(self, model_id: str) -> str:
        """Get model name from model ID using registry or heuristic."""
        if self.model_registry:
            # Try to find model in registry
            for model in self.model_registry.list_models():
                if model.get("bedrock_model_id") == model_id:
                    return model.get("name", model_id)
        
        # Heuristic: extract model name from model ID
        # e.g., "us.anthropic.claude-3-7-sonnet-20250219-v1:0" -> "Claude 3.7 Sonnet"
        if "claude" in model_id.lower():
            if "sonnet" in model_id.lower():
                version_match = re.search(r'claude-3-([\d.]+)-sonnet', model_id.lower())
                if version_match:
                    return f"Claude {version_match.group(1)} Sonnet"
                return "Claude Sonnet"
            elif "opus" in model_id.lower():
                return "Claude Opus"
            elif "haiku" in model_id.lower():
                return "Claude Haiku"
        elif "llama" in model_id.lower():
            return "Llama 3.2 11B Instruct"
        elif "nova" in model_id.lower():
            if "pro" in model_id.lower():
                return "Nova Pro"
            elif "lite" in model_id.lower():
                return "Nova Lite"
            elif "micro" in model_id.lower():
                return "Nova Micro"
            elif "premier" in model_id.lower():
                return "Nova Premier"
            return "Nova"
        elif "titan" in model_id.lower():
            return "Titan"
        
        return model_id
    
    def _extract_request_data(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Extract request data from log entry."""
        request_data = {}
        
        if "requestParameters" in entry:
            params = entry["requestParameters"]
            if isinstance(params, dict):
                request_data.update(params)
        
        # Check for input body
        if "input" in entry:
            input_data = entry["input"]
            if isinstance(input_data, dict):
                if "inputBodyJson" in input_data:
                    try:
                        body = json.loads(input_data["inputBodyJson"]) if isinstance(input_data["inputBodyJson"], str) else input_data["inputBodyJson"]
                        request_data.update(body)
                    except (json.JSONDecodeError, TypeError):
                        pass
        
        return request_data
    
    def _extract_response_data(self, entry: Dict[str, Any]) -> Dict[str, Any]:
        """Extract response data from log entry."""
        response_data = {}
        
        if "responseElements" in entry:
            response = entry["responseElements"]
            if isinstance(response, dict):
                response_data.update(response)
        
        # Check for output (common in Bedrock logs)
        if "output" in entry:
            output_data = entry["output"]
            if isinstance(output_data, dict):
                response_data.update(output_data)
                # Check for outputBodyJson (string that needs parsing)
                if "outputBodyJson" in output_data:
                    try:
                        body = json.loads(output_data["outputBodyJson"]) if isinstance(output_data["outputBodyJson"], str) else output_data["outputBodyJson"]
                        if isinstance(body, dict):
                            response_data.update(body)
                    except (json.JSONDecodeError, TypeError):
                        pass
                # Check for outputBody
                if "outputBody" in output_data:
                    try:
                        body = json.loads(output_data["outputBody"]) if isinstance(output_data["outputBody"], str) else output_data["outputBody"]
                        if isinstance(body, dict):
                            response_data.update(body)
                    except (json.JSONDecodeError, TypeError):
                        pass
        
        return response_data
    
    def _extract_input_tokens(self, entry: Dict[str, Any], request_data: Dict[str, Any]) -> int:
        """Extract input token count."""
        # Check usage in response
        if "usage" in entry:
            usage = entry["usage"]
            if isinstance(usage, dict):
                input_tokens = usage.get("inputTokens") or usage.get("input_tokens") or usage.get("promptTokenCount")
                if input_tokens:
                    return int(input_tokens)
        
        # Check in responseElements
        if "responseElements" in entry:
            response = entry["responseElements"]
            if isinstance(response, dict) and "usage" in response:
                usage = response["usage"]
                if isinstance(usage, dict):
                    input_tokens = usage.get("inputTokens") or usage.get("input_tokens")
                    if input_tokens:
                        return int(input_tokens)
        
        # Estimate from prompt if available
        prompt = self._extract_prompt(entry, request_data)
        if prompt:
            # Rough estimate: ~4 characters per token
            return int(len(prompt) / 4)
        
        return 0
    
    def _extract_output_tokens(self, entry: Dict[str, Any], response_data: Dict[str, Any]) -> int:
        """Extract output token count."""
        # Check usage in response (common in Bedrock logs)
        if "usage" in entry:
            usage = entry["usage"]
            if isinstance(usage, dict):
                output_tokens = usage.get("outputTokens") or usage.get("output_tokens") or usage.get("completionTokenCount") or usage.get("outputTokenCount")
                if output_tokens:
                    return int(output_tokens)
        
        # Check in output.usage
        if "output" in entry:
            output = entry["output"]
            if isinstance(output, dict):
                if "usage" in output:
                    usage = output["usage"]
                    if isinstance(usage, dict):
                        output_tokens = usage.get("outputTokens") or usage.get("output_tokens") or usage.get("outputTokenCount")
                        if output_tokens:
                            return int(output_tokens)
        
        # Check in responseElements
        if "responseElements" in entry:
            response = entry["responseElements"]
            if isinstance(response, dict):
                if "usage" in response:
                    usage = response["usage"]
                    if isinstance(usage, dict):
                        output_tokens = usage.get("outputTokens") or usage.get("output_tokens")
                        if output_tokens:
                            return int(output_tokens)
                
                # Check for generation token count (Meta Llama format)
                output_tokens = response.get("generationTokenCount") or response.get("generation_token_count")
                if output_tokens:
                    return int(output_tokens)
        
        # Estimate from response if available
        response_text = self._extract_response(entry, response_data)
        if response_text:
            # Rough estimate: ~4 characters per token
            return int(len(response_text) / 4)
        
        return 0
    
    def _extract_latency(self, entry: Dict[str, Any]) -> float:
        """Extract latency in milliseconds."""
        # Check for duration fields (common in Bedrock logs)
        if "duration" in entry:
            duration = entry["duration"]
            if isinstance(duration, (int, float)):
                # Assume duration is in milliseconds
                return float(duration)
            elif isinstance(duration, str):
                # Try to parse duration string
                try:
                    return float(duration)
                except ValueError:
                    pass
        
        # Check in output.duration
        if "output" in entry:
            output = entry["output"]
            if isinstance(output, dict) and "duration" in output:
                duration = output["duration"]
                if isinstance(duration, (int, float)):
                    return float(duration)
        
        # Calculate from timestamps if available
        if "eventTime" in entry and "requestTime" in entry:
            try:
                event_time = pd.to_datetime(entry["eventTime"])
                request_time = pd.to_datetime(entry["requestTime"])
                delta = (event_time - request_time).total_seconds() * 1000
                return float(delta)
            except Exception:
                pass
        
        # Try timestamp difference (if both start and end times available)
        if "timestamp" in entry:
            # Check if there's a start timestamp
            start_time = entry.get("startTime") or entry.get("requestTime")
            if start_time:
                try:
                    end_time = pd.to_datetime(entry["timestamp"], unit='ms' if isinstance(entry["timestamp"], (int, float)) else None)
                    start_time_dt = pd.to_datetime(start_time, unit='ms' if isinstance(start_time, (int, float)) else None)
                    delta = (end_time - start_time_dt).total_seconds() * 1000
                    return float(delta)
                except Exception:
                    pass
        
        return 0.0
    
    def _extract_prompt(self, entry: Dict[str, Any], request_data: Dict[str, Any]) -> Optional[str]:
        """Extract prompt text from request."""
        # Check messages array (Converse API format)
        if "messages" in request_data:
            messages = request_data["messages"]
            if isinstance(messages, list):
                user_messages = []
                for msg in messages:
                    if isinstance(msg, dict) and msg.get("role") == "user":
                        content = msg.get("content", [])
                        if isinstance(content, list):
                            for item in content:
                                if isinstance(item, dict) and "text" in item:
                                    user_messages.append(item["text"])
                                elif isinstance(item, str):
                                    user_messages.append(item)
                        elif isinstance(content, str):
                            user_messages.append(content)
                if user_messages:
                    return "\n\n".join(user_messages)
        
        # Check for inputText (Titan/Nova format)
        if "inputText" in request_data:
            return str(request_data["inputText"])
        
        # Check for prompt field
        if "prompt" in request_data:
            return str(request_data["prompt"])
        
        # Check in input.inputBodyJson (nested structure)
        if "input" in entry:
            input_data = entry["input"]
            if isinstance(input_data, dict):
                # Check for inputBodyJson string
                if "inputBodyJson" in input_data:
                    try:
                        body = json.loads(input_data["inputBodyJson"]) if isinstance(input_data["inputBodyJson"], str) else input_data["inputBodyJson"]
                        if isinstance(body, dict):
                            if "messages" in body:
                                messages = body["messages"]
                                if isinstance(messages, list):
                                    user_messages = []
                                    for msg in messages:
                                        if isinstance(msg, dict) and msg.get("role") == "user":
                                            content = msg.get("content", [])
                                            if isinstance(content, list):
                                                for item in content:
                                                    if isinstance(item, dict) and "text" in item:
                                                        user_messages.append(item["text"])
                                            elif isinstance(content, str):
                                                user_messages.append(content)
                                    if user_messages:
                                        return "\n\n".join(user_messages)
                            if "inputText" in body:
                                return str(body["inputText"])
                            if "prompt" in body:
                                return str(body["prompt"])
                    except (json.JSONDecodeError, TypeError):
                        pass
        
        return None
    
    def _extract_response(self, entry: Dict[str, Any], response_data: Dict[str, Any]) -> Optional[str]:
        """Extract response text."""
        # Check for output message (Converse API format)
        if "output" in response_data:
            output = response_data["output"]
            if isinstance(output, dict) and "message" in output:
                message = output["message"]
                if isinstance(message, dict) and "content" in message:
                    content = message["content"]
                    if isinstance(content, list):
                        texts = []
                        for item in content:
                            if isinstance(item, dict) and "text" in item:
                                texts.append(item["text"])
                            elif isinstance(item, str):
                                texts.append(item)
                        if texts:
                            return "\n".join(texts)
        
        # Check in entry.output (nested structure)
        if "output" in entry:
            output = entry["output"]
            if isinstance(output, dict):
                # Check for outputBodyJson string
                if "outputBodyJson" in output:
                    try:
                        body = json.loads(output["outputBodyJson"]) if isinstance(output["outputBodyJson"], str) else output["outputBodyJson"]
                        if isinstance(body, dict):
                            # Check for output.message.content (Converse API)
                            if "output" in body and isinstance(body["output"], dict):
                                msg = body["output"].get("message", {})
                                if isinstance(msg, dict) and "content" in msg:
                                    content = msg["content"]
                                    if isinstance(content, list):
                                        texts = []
                                        for item in content:
                                            if isinstance(item, dict) and "text" in item:
                                                texts.append(item["text"])
                                        if texts:
                                            return "\n".join(texts)
                            # Check for results array
                            if "results" in body:
                                results = body["results"]
                                if isinstance(results, list) and len(results) > 0:
                                    result = results[0]
                                    if isinstance(result, dict):
                                        return result.get("outputText") or result.get("text")
                            # Check for generation field
                            if "generation" in body:
                                return str(body["generation"])
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # Check for direct message structure
                if "message" in output:
                    message = output["message"]
                    if isinstance(message, dict) and "content" in message:
                        content = message["content"]
                        if isinstance(content, list):
                            texts = []
                            for item in content:
                                if isinstance(item, dict) and "text" in item:
                                    texts.append(item["text"])
                            if texts:
                                return "\n".join(texts)
        
        # Check for results array (Titan/Nova format)
        if "results" in response_data:
            results = response_data["results"]
            if isinstance(results, list) and len(results) > 0:
                result = results[0]
                if isinstance(result, dict):
                    return result.get("outputText") or result.get("text")
        
        # Check for generation field (Meta Llama format)
        if "generation" in response_data:
            return str(response_data["generation"])
        
        # Check for completion field
        if "completion" in response_data:
            return str(response_data["completion"])
        
        return None
    
    def _has_error(self, entry: Dict[str, Any]) -> bool:
        """Check if entry has an error."""
        if "errorCode" in entry or "errorMessage" in entry:
            return True
        if "error" in entry:
            return True
        return False
    
    def _extract_error(self, entry: Dict[str, Any]) -> Optional[str]:
        """Extract error message."""
        if "errorMessage" in entry:
            return str(entry["errorMessage"])
        if "error" in entry:
            error = entry["error"]
            if isinstance(error, dict):
                return error.get("message") or str(error)
            return str(error)
        return None
    
    def _calculate_costs(self, model_id: str, input_tokens: int, output_tokens: int) -> tuple:
        """Calculate costs based on model pricing."""
        if not self.model_registry:
            return 0.0, 0.0, 0.0
        
        # Find model in registry
        for model in self.model_registry.list_models():
            if model.get("bedrock_model_id") == model_id:
                pricing = self.model_registry.get_model_pricing(model)
                input_cost = (input_tokens / 1000.0) * pricing.get("input_per_1k_tokens_usd", 0.0)
                output_cost = (output_tokens / 1000.0) * pricing.get("output_per_1k_tokens_usd", 0.0)
                total_cost = input_cost + output_cost
                return round(input_cost, 6), round(output_cost, 6), round(total_cost, 6)
        
        return 0.0, 0.0, 0.0

