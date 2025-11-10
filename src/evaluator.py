"""Evaluator core: runs prompts against Bedrock models and collects metrics."""

import json
import uuid
import io
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

import boto3
from botocore.exceptions import ClientError, BotoCoreError

from src.utils.bedrock_client import get_bedrock_client
from src.utils.timing import Stopwatch
from src.utils.json_utils import is_valid_json
from src.tokenizers import count_tokens
from src.model_registry import ModelRegistry


class BedrockEvaluator:
    """Evaluates prompts against Bedrock models and collects performance metrics."""
    
    def __init__(
        self,
        model_registry: ModelRegistry,
        region_name: Optional[str] = None,
        max_retries: int = 3
    ):
        self.model_registry = model_registry
        self.region_name = region_name or model_registry.region_name
        self.bedrock_client = get_bedrock_client(self.region_name)
        self.max_retries = max_retries
    
    def evaluate_prompt(
        self,
        prompt: str,
        model: Dict[str, Any],
        prompt_id: Optional[int] = None,
        expected_json: bool = False,
        run_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a single prompt against a model.
        
        Args:
            prompt: The prompt text to evaluate
            model: Model configuration dictionary
            prompt_id: Optional prompt identifier
            expected_json: Whether JSON response is expected
            run_id: Optional run identifier for grouping
        
        Returns:
            Dictionary with evaluation metrics
        """
        if run_id is None:
            run_id = str(uuid.uuid4())[:8]
        
        model_name = model.get("name", "unknown")
        model_id = model.get("bedrock_model_id", "unknown")
        provider = model.get("provider", "").lower()
        tokenizer_type = model.get("tokenizer", "heuristic")
        
        # Count input tokens
        input_tokens = count_tokens(tokenizer_type, prompt)
        
        # Prepare generation parameters
        gen_params = self.model_registry.get_generation_params(model)
        
        # Initialize metrics
        metrics = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "run_id": run_id,
            "model_name": model_name,
            "model_id": model_id,
            "prompt_id": prompt_id,
            "input_prompt": prompt,  # Store the input prompt for display
            "input_tokens": input_tokens,
            "output_tokens": 0,
            "latency_ms": 0,
            "json_valid": False,
            "error": None,
            "status": "success",
            "cost_usd_input": 0.0,
            "cost_usd_output": 0.0,
            "cost_usd_total": 0.0,
        }
        
        # Make API call with timing
        timer = None
        try:
            with Stopwatch() as timer:
                response_text, output_tokens_actual, input_tokens_actual = self._invoke_model(
                    prompt, model, provider, gen_params
                )
            
            metrics["latency_ms"] = timer.elapsed_ms
            metrics["output_tokens"] = output_tokens_actual
            
            # Use actual input tokens from API if available, otherwise use estimated
            if input_tokens_actual > 0:
                metrics["input_tokens"] = input_tokens_actual
                input_tokens = input_tokens_actual  # Use actual for cost calculation
            
            # Store full response for dashboard display (can be long, but needed for JSON output viewing)
            metrics["response"] = response_text  # Store full response
            
            # Always validate JSON to provide useful information
            # Check if response is empty first
            if not response_text or not response_text.strip() or output_tokens_actual == 0:
                # No response generated - cannot validate JSON
                if expected_json:
                    metrics["json_valid"] = False  # Expected JSON but got empty response
                else:
                    metrics["json_valid"] = None  # Not applicable - no response
            else:
                # Try to extract/clean JSON from response (handles markdown code blocks, etc.)
                # Store original response for debugging
                original_response = response_text
                is_valid, cleaned_json = self._validate_json_with_cleaning(response_text)
                
                # If validation failed and JSON was expected, try once more with more aggressive cleaning
                if not is_valid and expected_json:
                    # Try removing common prefixes/suffixes that models sometimes add
                    cleaned_response = response_text.strip()
                    # Remove common prefixes
                    prefixes_to_remove = [
                        "Here's the JSON:",
                        "Here is the JSON:",
                        "The JSON response is:",
                        "JSON:",
                        "```json",
                        "```",
                    ]
                    for prefix in prefixes_to_remove:
                        if cleaned_response.lower().startswith(prefix.lower()):
                            cleaned_response = cleaned_response[len(prefix):].strip()
                            # Remove leading colon if present
                            if cleaned_response.startswith(':'):
                                cleaned_response = cleaned_response[1:].strip()
                    
                    # Remove common suffixes
                    suffixes_to_remove = [
                        "```",
                        "Hope this helps!",
                        "Let me know if you need anything else.",
                    ]
                    for suffix in suffixes_to_remove:
                        if cleaned_response.lower().endswith(suffix.lower()):
                            cleaned_response = cleaned_response[:-len(suffix)].strip()
                    
                    # Try validation again with cleaned response
                    if cleaned_response != response_text:
                        is_valid, cleaned_json = self._validate_json_with_cleaning(cleaned_response)
                
                if expected_json:
                    # If JSON was expected, use the validation result directly
                    metrics["json_valid"] = is_valid
                    # Store cleaned JSON if available for better display
                    if is_valid and cleaned_json:
                        metrics["cleaned_response"] = cleaned_json
                    # Store original response for debugging if validation failed
                    elif not is_valid:
                        metrics["original_response"] = original_response[:500]  # First 500 chars for debugging
                else:
                    # If JSON wasn't expected, still validate and show result
                    # This helps users see if their response happens to be valid JSON
                    metrics["json_valid"] = is_valid if is_valid else False  # Show False instead of None
                    if is_valid and cleaned_json:
                        metrics["cleaned_response"] = cleaned_json
            
            # Calculate costs using actual token counts from API
            pricing = self.model_registry.get_model_pricing(model)
            input_cost = (input_tokens / 1000.0) * pricing["input_per_1k_tokens_usd"]
            output_cost = (output_tokens_actual / 1000.0) * pricing["output_per_1k_tokens_usd"]
            
            metrics["cost_usd_input"] = round(input_cost, 6)
            metrics["cost_usd_output"] = round(output_cost, 6)
            metrics["cost_usd_total"] = round(input_cost + output_cost, 6)
            
        except Exception as e:
            metrics["status"] = "error"
            error_str = str(e)
            metrics["error"] = error_str
            
            # Enhance error message for Anthropic access errors
            if "use case details" in error_str.lower() and "ResourceNotFoundException" in error_str:
                # The error message already includes helpful instructions, so we can enhance it
                if "TO FIX THIS ERROR" not in error_str:
                    region = self.region_name
                    metrics["error"] = (
                        f"Bedrock API error (ResourceNotFoundException): Model use case details have not been submitted for this account. "
                        f"Fill out the Anthropic use case details form before using the model. "
                        f"If you have already filled out the form, try again in 15 minutes. "
                        f"(tried model ID: {model_id})\n\n"
                        f"🔧 TO FIX THIS ERROR:\n"
                        f"1. Go to AWS Bedrock Model Access: https://console.aws.amazon.com/bedrock/home?region={region}#/modelaccess\n"
                        f"2. Find 'Anthropic' in the provider list\n"
                        f"3. Click 'Request model access' or 'Enable'\n"
                        f"4. Fill out the use case form and submit\n"
                        f"5. Wait 5-15 minutes for approval\n"
                        f"6. Try again after approval\n\n"
                        f"See MANUAL_GUIDE.md section 'Issue 3.5' or FIX_ANTHROPIC_ACCESS.md for detailed instructions."
                    )
            
            metrics["latency_ms"] = timer.elapsed_ms if timer is not None and 'timer' in locals() else 0
            # Make sure input tokens are captured even on error
            if metrics["input_tokens"] == 0:
                metrics["input_tokens"] = input_tokens
        
        return metrics
    
    def _invoke_model(
        self,
        prompt: str,
        model: Dict[str, Any],
        provider: str,
        gen_params: Dict[str, Any]
    ) -> Tuple[str, int, int]:
        """
        Invoke Bedrock model and return response text and token count.
        
        Returns:
            Tuple of (response_text, output_tokens)
        """
        model_id = model.get("bedrock_model_id")
        tokenizer_type = model.get("tokenizer", "heuristic")
        use_inference_profile = model.get("use_inference_profile", False)
        
        # Use Converse API for Anthropic Claude models and Amazon Nova models
        if provider == "anthropic" or "claude" in model_id.lower() or "nova" in model_id.lower():
            return self._invoke_converse(prompt, model_id, gen_params, tokenizer_type, use_inference_profile)
        
        # Use InvokeModel for other models (Llama, Titan, etc.)
        return self._invoke_model_direct(prompt, model_id, provider, gen_params, tokenizer_type, use_inference_profile)
    
    def _invoke_converse(
        self,
        prompt: str,
        model_id: str,
        gen_params: Dict[str, Any],
        tokenizer_type: str,
        use_inference_profile: bool = False
    ) -> Tuple[str, int, int]:
        """Invoke models using Converse API (Anthropic Claude and Amazon Nova)."""
        # Build model ID variants - prioritize inference profiles if needed
        model_id_without_suffix = model_id.rsplit(":", 1)[0] if ":" in model_id else model_id
        
        # Start with inference profile variants if needed, then try direct model IDs
        model_id_variants = []
        
        if use_inference_profile or "us." in model_id or "global." in model_id:
            # Already an inference profile ID - use as-is first
            model_id_variants.append(model_id)
        else:
            # Try inference profile first (for us-east-2 region)
            if self.region_name == "us-east-2":
                model_id_variants.append(f"us.{model_id}")
                model_id_variants.append(f"us.{model_id_without_suffix}:0")
            # Then try direct model IDs
            model_id_variants.extend([
                model_id,  # Original model ID
                model_id_without_suffix,  # Without version suffix
            ])
        
        model_id_variants = list(dict.fromkeys(model_id_variants))  # Remove duplicates while preserving order
        
        body = {
            "messages": [
                {
                    "role": "user",
                    "content": [{"text": prompt}]
                }
            ],
            "maxTokens": gen_params.get("max_tokens", 512),
            "temperature": gen_params.get("temperature", 0.2),
            "topP": gen_params.get("top_p", 0.95)
        }
        
        last_error = None
        for variant_id in model_id_variants:
            try:
                response = self.bedrock_client.converse(
                    modelId=variant_id,
                    messages=body["messages"],
                    inferenceConfig={
                        "maxTokens": body["maxTokens"],
                        "temperature": body["temperature"],
                        "topP": body["topP"]
                    }
                )
                
                # Extract response text
                content = response.get("output", {}).get("message", {}).get("content", [])
                response_text = ""
                for item in content:
                    if isinstance(item, dict) and "text" in item:
                        response_text += item["text"]
                    elif isinstance(item, str):
                        response_text += item
                
                # Get actual token usage from Converse API response
                usage = response.get("usage", {})
                input_tokens_api = usage.get("inputTokens", 0)  # Actual input tokens from API
                output_tokens = usage.get("outputTokens", 0)    # Actual output tokens from API
                
                # If output tokens not available, estimate
                if output_tokens == 0:
                    output_tokens = count_tokens(tokenizer_type, response_text)
                
                # Return: (response_text, output_tokens, input_tokens)
                return response_text, output_tokens, input_tokens_api
                
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_msg = e.response.get("Error", {}).get("Message", str(e))
                
                # Provide helpful message for Anthropic access errors
                if error_code == "ResourceNotFoundException" and "use case details" in error_msg.lower():
                    region = self.region_name
                    last_error = (
                        f"Bedrock API error (ResourceNotFoundException): Model use case details have not been submitted for this account. "
                        f"Fill out the Anthropic use case details form before using the model. "
                        f"If you have already filled out the form, try again in 15 minutes. "
                        f"(tried model ID: {variant_id})\n\n"
                        f"🔧 TO FIX THIS ERROR:\n"
                        f"1. Go to AWS Bedrock Model Access: https://console.aws.amazon.com/bedrock/home?region={region}#/modelaccess\n"
                        f"2. Find 'Anthropic' in the provider list\n"
                        f"3. Click 'Request model access' or 'Enable'\n"
                        f"4. Fill out the use case form and submit\n"
                        f"5. Wait 5-15 minutes for approval\n"
                        f"6. Try again after approval\n\n"
                        f"See MANUAL_GUIDE.md section 'Issue 3.5' or FIX_ANTHROPIC_ACCESS.md for detailed instructions."
                    )
                    raise Exception(last_error)
                
                last_error = f"Bedrock API error ({error_code}): {error_msg} (tried model ID: {variant_id})"
                
                # If error mentions inference profile, try inference profile variants
                if "inference profile" in error_msg.lower() or "on-demand throughput" in error_msg.lower():
                    if not variant_id.startswith("us.") and not variant_id.startswith("global."):
                        # Try with inference profile prefix
                        inference_profile_id = f"us.{variant_id}"
                        if inference_profile_id not in model_id_variants:
                            model_id_variants.append(inference_profile_id)
                    continue
                
                # If it's not a ValidationException, don't try other variants
                if error_code != "ValidationException":
                    raise Exception(last_error)
            except Exception as e:
                error_str = str(e)
                last_error = f"Failed to invoke model with ID '{variant_id}': {error_str}"
                
                # Check if error mentions inference profile
                if "inference profile" in error_str.lower() or "on-demand throughput" in error_str.lower():
                    if not variant_id.startswith("us.") and not variant_id.startswith("global."):
                        inference_profile_id = f"us.{variant_id}"
                        if inference_profile_id not in model_id_variants:
                            model_id_variants.append(inference_profile_id)
                    continue
                
                # Continue to next variant only if it's a validation error
                if "ValidationException" not in error_str:
                    raise Exception(last_error)
        
        # If all variants failed, raise the last error with all attempted IDs
        attempted_ids = ", ".join([f"'{id}'" for id in model_id_variants])
        raise Exception(f"{last_error} All attempted model IDs: {attempted_ids}")
    
    def _invoke_model_direct(
        self,
        prompt: str,
        model_id: str,
        provider: str,
        gen_params: Dict[str, Any],
        tokenizer_type: str,
        use_inference_profile: bool = False
    ) -> Tuple[str, int, int]:
        """Invoke model using InvokeModel API (for non-Claude models)."""
        # Build model ID variants - prioritize inference profiles if needed
        model_id_without_suffix = model_id.rsplit(":", 1)[0] if ":" in model_id else model_id
        model_id_variants = []
        
        if use_inference_profile or "us." in model_id or "global." in model_id:
            # Already an inference profile ID - use as-is first
            model_id_variants.append(model_id)
        else:
            # Try inference profile first (for us-east-2 region)
            if self.region_name == "us-east-2":
                model_id_variants.append(f"us.{model_id}")
                model_id_variants.append(f"us.{model_id_without_suffix}:0")
            # Then try direct model IDs
            model_id_variants.append(model_id)
            # For Meta Llama models, try different formats
            if provider == "meta" or "llama" in model_id.lower():
                if model_id_without_suffix != model_id:
                    model_id_variants.append(model_id_without_suffix)
                if ":" not in model_id:
                    model_id_variants.append(f"{model_id}:0")
        
        model_id_variants = list(dict.fromkeys(model_id_variants))  # Remove duplicates
        
        last_error = None
        for variant_id in model_id_variants:
            try:
                return self._try_invoke_model_direct(
                    prompt, variant_id, provider, gen_params, tokenizer_type
                )
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "Unknown")
                error_msg = e.response.get("Error", {}).get("Message", str(e))
                last_error = f"Bedrock API error ({error_code}): {error_msg} (tried model ID: {variant_id})"
                
                # If error mentions inference profile, try inference profile variants
                if "inference profile" in error_msg.lower() or "on-demand throughput" in error_msg.lower():
                    if not variant_id.startswith("us.") and not variant_id.startswith("global."):
                        inference_profile_id = f"us.{variant_id}"
                        if inference_profile_id not in model_id_variants:
                            model_id_variants.append(inference_profile_id)
                    continue
                
                if error_code != "ValidationException":
                    raise Exception(last_error)
            except Exception as e:
                error_str = str(e)
                last_error = f"Failed to invoke model with ID '{variant_id}': {error_str}"
                
                # Check if error mentions inference profile
                if "inference profile" in error_str.lower() or "on-demand throughput" in error_str.lower():
                    if not variant_id.startswith("us.") and not variant_id.startswith("global."):
                        inference_profile_id = f"us.{variant_id}"
                        if inference_profile_id not in model_id_variants:
                            model_id_variants.append(inference_profile_id)
                    continue
                
                if "ValidationException" not in error_str:
                    raise Exception(last_error)
        
        # If all variants failed
        attempted_ids = ", ".join([f"'{id}'" for id in model_id_variants])
        raise Exception(f"{last_error} All attempted model IDs: {attempted_ids}")
    
    def _try_invoke_model_direct(
        self,
        prompt: str,
        model_id: str,
        provider: str,
        gen_params: Dict[str, Any],
        tokenizer_type: str
    ) -> Tuple[str, int, int]:
        """Helper method to try invoking a model with a specific model ID."""
        try:
            # Prepare request body based on provider
            if provider == "meta" or "llama" in model_id.lower():
                # Meta Llama models - format prompt for Llama Instruct models
                # Llama Instruct models expect a specific chat format
                # For Llama 3.1/3.2, we need to use the chat template format
                formatted_prompt = prompt
                
                # If the prompt doesn't already have the chat format, add it
                # Llama 3.1/3.2 Instruct models use: <|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n
                if not prompt.strip().startswith("<|begin_of_text|>") and "instruct" in model_id.lower():
                    # Format as Llama chat prompt
                    formatted_prompt = f"<|begin_of_text|><|start_header_id|>user<|end_header_id|>\n\n{prompt}<|eot_id|><|start_header_id|>assistant<|end_header_id|>\n\n"
                
                body = json.dumps({
                    "prompt": formatted_prompt,
                    "max_gen_len": gen_params.get("max_tokens", 512),
                    "temperature": gen_params.get("temperature", 0.2),
                    "top_p": gen_params.get("top_p", 0.9)
                    # Note: Not adding stop sequences here as they may cause empty responses
                })
            elif provider == "amazon" or "titan" in model_id.lower() or "nova" in model_id.lower():
                # Amazon models (Titan, Nova) use inputText format
                body = json.dumps({
                    "inputText": prompt,
                    "textGenerationConfig": {
                        "maxTokenCount": gen_params.get("max_tokens", 512),
                        "temperature": gen_params.get("temperature", 0.2),
                        "topP": gen_params.get("top_p", 0.9)
                    }
                })
            elif provider == "alibaba" or "qwen" in model_id.lower():
                # Alibaba Qwen models - may use similar format to Meta or generic
                # Try generic format first, may need adjustment based on actual API
                body = json.dumps({
                    "prompt": prompt,
                    "max_tokens": gen_params.get("max_tokens", 512),
                    "temperature": gen_params.get("temperature", 0.2),
                    "top_p": gen_params.get("top_p", 0.9)
                })
            else:
                # Generic format
                body = json.dumps({
                    "prompt": prompt,
                    "max_tokens": gen_params.get("max_tokens", 512),
                    "temperature": gen_params.get("temperature", 0.2),
                    "top_p": gen_params.get("top_p", 0.9)
                })
            
            response = self.bedrock_client.invoke_model(
                modelId=model_id,
                body=body,
                contentType="application/json",
                accept="application/json"
            )
            
            # Parse response - ensure body is read correctly
            response_body_stream = response["body"]
            if hasattr(response_body_stream, 'read'):
                # Reset stream position if possible
                try:
                    response_body_stream.seek(0)
                except (AttributeError, io.UnsupportedOperation):
                    pass
                response_body_raw = response_body_stream.read()
            else:
                response_body_raw = response_body_stream
            
            # Decode if bytes
            if isinstance(response_body_raw, bytes):
                response_body_raw = response_body_raw.decode('utf-8')
            
            try:
                response_body = json.loads(response_body_raw)
            except json.JSONDecodeError as e:
                # If JSON parsing fails, log the raw response for debugging
                raise Exception(f"Failed to parse response as JSON. Raw response (first 500 chars): {response_body_raw[:500]}. Error: {e}")
            
            # Extract text based on provider
            if provider == "meta" or "llama" in model_id.lower():
                # Meta Llama models return response in "generation" field
                # Check all possible fields systematically
                response_text = ""
                
                # Debug: Log response body keys for troubleshooting
                response_keys = list(response_body.keys()) if isinstance(response_body, dict) else []
                
                # Primary field for Llama models - this is the standard field
                if "generation" in response_body:
                    response_text = response_body["generation"]
                # Secondary fields
                elif "generated_text" in response_body:
                    response_text = response_body["generated_text"]
                elif "output" in response_body:
                    response_text = response_body["output"]
                elif "text" in response_body:
                    response_text = response_body["text"]
                # Check nested results array
                elif "results" in response_body:
                    results = response_body.get("results", [])
                    if results and isinstance(results, list) and len(results) > 0:
                        first_result = results[0]
                        response_text = (
                            first_result.get("generated_text", "") or
                            first_result.get("text", "") or
                            first_result.get("output", "") or
                            first_result.get("generation", "")
                        )
                else:
                    # If no standard fields found, log available keys for debugging
                    # This helps identify if response format is different
                    if not response_text:
                        # Try to find any string field that might contain the response
                        for key, value in response_body.items():
                            if isinstance(value, str) and len(value) > 10:
                                response_text = value
                                break
                
                # Ensure response_text is a string
                if not isinstance(response_text, str):
                    response_text = str(response_text) if response_text else ""
                
                # Check for token usage in Meta Llama response
                # Meta Llama returns: prompt_token_count, generation_token_count
                generation_token_count = response_body.get("generation_token_count", 0)
                prompt_token_count = response_body.get("prompt_token_count", 0)
                
                # Also check usage object if present
                usage = response_body.get("usage", {})
                output_tokens = (
                    generation_token_count or
                    usage.get("completion_tokens") or 
                    usage.get("generation_tokens") or 
                    usage.get("output_tokens") or 0
                )
                
                # If generation_token_count > 0 but response_text is empty, 
                # the model might have generated only a stop token or whitespace
                if generation_token_count > 0 and not response_text.strip():
                    # Check stop_reason to understand why
                    stop_reason = response_body.get("stop_reason", "unknown")
                    response_text = f"[WARNING: Model generated {generation_token_count} token(s) but output is empty. Stop reason: {stop_reason}. This may indicate the model hit a stop sequence immediately or generated only whitespace.]"
                # If output_tokens is 0 but we have response_text, estimate tokens
                elif output_tokens == 0 and response_text:
                    output_tokens = count_tokens(tokenizer_type, response_text)
                # If we have generation_token_count but no response_text, use it for output_tokens
                elif output_tokens == 0 and generation_token_count > 0:
                    output_tokens = generation_token_count
                
                # If still no response and no tokens, this might indicate an API issue
                if not response_text and output_tokens == 0:
                    # Log the response structure for debugging (first 1000 chars)
                    debug_info = json.dumps(response_body, indent=2)[:1000]
                    response_text = f"[DEBUG: No generation found. Response keys: {response_keys}. Response body: {debug_info}]"
            elif provider == "amazon" or "titan" in model_id.lower() or "nova" in model_id.lower():
                result = response_body.get("results", [{}])[0] if response_body.get("results") else {}
                response_text = result.get("outputText", "")
                # Check for token usage in Amazon model response (Titan, Nova)
                # Titan/Nova may return: usage.inputTextTokenCount, usage.results[0].tokenCount
                usage = result.get("usage", {})
                output_tokens = usage.get("tokenCount") or usage.get("outputTokenCount") or 0
            elif provider == "alibaba" or "qwen" in model_id.lower():
                # Alibaba Qwen models - try various response formats
                response_text = (
                    response_body.get("completion", "") or 
                    response_body.get("generated_text", "") or
                    response_body.get("output", "") or
                    response_body.get("text", "")
                )
                # Check for generic token usage fields
                usage = response_body.get("usage", {})
                output_tokens = usage.get("output_tokens") or usage.get("completion_tokens") or usage.get("generation_tokens") or 0
            else:
                response_text = response_body.get("completion", "") or response_body.get("generated_text", "")
                # Check for generic token usage fields
                usage = response_body.get("usage", {})
                output_tokens = usage.get("output_tokens") or usage.get("completion_tokens") or usage.get("generation_tokens") or 0
            
            # If no token usage found in API response, estimate
            if output_tokens == 0:
                output_tokens = count_tokens(tokenizer_type, response_text)
            
            # Try to get actual input tokens using CountTokens API
            input_tokens_api = self._get_actual_input_tokens(prompt, model_id, provider)
            
            # Return: (response_text, output_tokens, input_tokens)
            return response_text, output_tokens, input_tokens_api
            
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_msg = e.response.get("Error", {}).get("Message", str(e))
            raise Exception(f"Bedrock API error ({error_code}): {error_msg}")
        except Exception as e:
            raise Exception(f"Failed to invoke model: {str(e)}")
    
    def _get_actual_input_tokens(
        self,
        prompt: str,
        model_id: str,
        provider: str
    ) -> int:
        """
        Get actual input token count using AWS Bedrock CountTokens API.
        
        This API returns the exact token count that would be charged,
        providing accurate cost calculation.
        
        Returns:
            Actual input token count, or 0 if API is not available/unsupported
        """
        try:
            # CountTokens API is available for supported models
            # Format request body based on provider
            if provider == "anthropic" or "nova" in model_id.lower():
                # For Anthropic and Nova models, use Converse API format
                body = {
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"text": prompt}]
                        }
                    ]
                }
            elif provider == "meta" or "llama" in model_id.lower():
                body = {"prompt": prompt}
            elif provider == "amazon" or "titan" in model_id.lower() or "nova" in model_id.lower():
                body = {"inputText": prompt}
            elif provider == "alibaba" or "qwen" in model_id.lower():
                body = {"prompt": prompt}
            else:
                body = {"prompt": prompt}
            
            # Call CountTokens API if available
            # Note: CountTokens API may not be available in all boto3 versions/regions
            if hasattr(self.bedrock_client, 'count_tokens'):
                response = self.bedrock_client.count_tokens(
                    modelId=model_id,
                    body=json.dumps(body),
                    contentType="application/json"
                )
                
                # Parse response - handle both dict and readable stream
                body_data = response.get("body", {})
                if hasattr(body_data, "read"):
                    response_body = json.loads(body_data.read())
                elif isinstance(body_data, dict):
                    response_body = body_data
                elif isinstance(body_data, str):
                    response_body = json.loads(body_data)
                else:
                    response_body = {}
                
                # Extract token count - CountTokens API returns totalTokens
                total_tokens = response_body.get("totalTokens", 0) or \
                              response_body.get("inputTokenCount", 0) or \
                              response_body.get("tokenCount", 0)
                
                if total_tokens > 0:
                    return int(total_tokens)
            
            # If CountTokens API is not available, return 0 to use estimation
            return 0
            
        except AttributeError:
            # Method doesn't exist in this boto3 version
            return 0
        except ClientError as e:
            # API error - CountTokens may not be available for this model/region
            return 0
        except Exception as e:
            # Any other error - fall back to estimation
            return 0
    
    def evaluate_prompts_batch(
        self,
        prompts_df,
        models: List[Dict[str, Any]],
        run_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Evaluate multiple prompts against multiple models.
        
        Args:
            prompts_df: DataFrame with columns: prompt_id, prompt, expected_json (optional)
            models: List of model configurations
            run_id: Optional run identifier
        
        Returns:
            List of metrics dictionaries
        """
        if run_id is None:
            run_id = str(uuid.uuid4())[:8]
        
        all_metrics = []
        
        for _, row in prompts_df.iterrows():
            prompt_id = row.get("prompt_id", None)
            prompt = row.get("prompt", "")
            expected_json = bool(row.get("expected_json", False))
            
            if not prompt:
                continue
            
            # Evaluate against each model
            for model in models:
                metrics = self.evaluate_prompt(
                    prompt=prompt,
                    model=model,
                    prompt_id=prompt_id,
                    expected_json=expected_json,
                    run_id=run_id
                )
                all_metrics.append(metrics)
        
        return all_metrics
    
    def _validate_json_with_cleaning(self, text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate JSON with cleaning/extraction logic.
        Handles markdown code blocks, wrapped JSON, etc.
        
        Returns:
            Tuple of (is_valid, cleaned_json_text)
        """
        if not text or not text.strip():
            return False, None
        
        import re
        
        # First try direct validation
        try:
            json.loads(text.strip())
            return True, text.strip()
        except (json.JSONDecodeError, TypeError):
            pass
        
        # Try to extract JSON from markdown code blocks
        # Pattern: ```json ... ``` or ``` ... ```
        json_block_patterns = [
            r'```json\s*\n(.*?)\n```',
            r'```\s*\n(.*?)\n```',
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'```json\s*(.*?)```',  # No newlines
            r'```\s*(.*?)```',  # No newlines
        ]
        
        for pattern in json_block_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            for match in matches:
                try:
                    cleaned = match.strip()
                    json.loads(cleaned)
                    return True, cleaned
                except (json.JSONDecodeError, TypeError):
                    continue
        
        # Try to find JSON object/array in the text
        # Look for balanced brackets - try both { } and [ ]
        text_clean = text.strip()
        
        # Find first { or [
        for start_char, end_char in [('{', '}'), ('[', ']')]:
            start_idx = text_clean.find(start_char)
            if start_idx >= 0:
                # Find matching closing bracket
                bracket_count = 0
                in_string = False
                escape_next = False
                last_valid_end = -1
                
                for i in range(start_idx, len(text_clean)):
                    char = text_clean[i]
                    
                    if escape_next:
                        escape_next = False
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        continue
                    
                    if not in_string:
                        if char == start_char:
                            bracket_count += 1
                        elif char == end_char:
                            bracket_count -= 1
                            if bracket_count == 0:
                                # Found matching bracket
                                json_candidate = text_clean[start_idx:i+1]
                                try:
                                    json.loads(json_candidate)
                                    return True, json_candidate
                                except (json.JSONDecodeError, TypeError):
                                    # Store this as potential end point
                                    last_valid_end = i
                                    break
                    
                    # If we've gone too far without finding a match, try to use last valid end
                    if i - start_idx > 50000:  # Safety limit
                        break
                
                # If we found a start but no exact match, try to extract from start to last valid end
                if last_valid_end > start_idx:
                    json_candidate = text_clean[start_idx:last_valid_end+1]
                    try:
                        json.loads(json_candidate)
                        return True, json_candidate
                    except (json.JSONDecodeError, TypeError):
                        pass
                
                # Last resort: try to find a reasonable end point by looking for the last closing bracket
                if bracket_count > 0:
                    end_idx = text_clean.rfind(end_char)
                    if end_idx > start_idx:
                        json_candidate = text_clean[start_idx:end_idx+1]
                        try:
                            json.loads(json_candidate)
                            return True, json_candidate
                        except (json.JSONDecodeError, TypeError):
                            pass
        
        # Additional fallback: Try regex to find JSON-like structures
        # Look for arrays or objects that might be valid JSON
        # Use non-greedy matching first, then try greedy
        json_patterns = [
            r'\[[\s\S]*?\]',  # Array pattern (non-greedy)
            r'\{[\s\S]*?\}',  # Object pattern (non-greedy)
            r'\[[\s\S]+\]',  # Array pattern (greedy)
            r'\{[\s\S]+\}',  # Object pattern (greedy)
        ]
        
        # Try to find the longest valid JSON match
        best_match = None
        best_match_len = 0
        
        for pattern in json_patterns:
            matches = re.finditer(pattern, text, re.DOTALL)
            for match in matches:
                json_candidate = match.group(0)
                try:
                    json.loads(json_candidate)
                    # Prefer longer matches (more complete JSON)
                    if len(json_candidate) > best_match_len:
                        best_match = json_candidate
                        best_match_len = len(json_candidate)
                except (json.JSONDecodeError, TypeError):
                    continue
        
        if best_match:
            return True, best_match
        
        # Final attempt: Try to extract JSON by finding the first [ or { and the last ] or }
        # This handles cases where there's explanatory text before/after
        first_bracket = text.find('[')
        first_brace = text.find('{')
        
        # Find the earliest bracket
        if first_bracket >= 0 and (first_brace < 0 or first_bracket < first_brace):
            # Look for array
            last_bracket = text.rfind(']')
            if last_bracket > first_bracket:
                candidate = text[first_bracket:last_bracket+1]
                try:
                    json.loads(candidate)
                    return True, candidate
                except (json.JSONDecodeError, TypeError):
                    pass
        
        if first_brace >= 0:
            # Look for object
            last_brace = text.rfind('}')
            if last_brace > first_brace:
                candidate = text[first_brace:last_brace+1]
                try:
                    json.loads(candidate)
                    return True, candidate
                except (json.JSONDecodeError, TypeError):
                    pass
        
        return False, None
