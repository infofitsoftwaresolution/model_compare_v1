"""Premium Streamlit Dashboard for LLM Model Comparison - Enterprise Edition"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import time
import json

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Load environment variables from .env file if it exists
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

# Import evaluation components
from src.model_registry import ModelRegistry
from src.evaluator import BedrockEvaluator
from src.metrics_logger import MetricsLogger
from src.report_generator import ReportGenerator
from src.utils.json_utils import is_valid_json
from src.cloudwatch_parser import CloudWatchParser
import tempfile
import os


def extract_full_prompt_text(item: dict) -> str:
    """
    Extract the FULL prompt text (all user messages combined) from JSON structures.
    This is used for CSV conversion - it returns the complete text without extracting questions.
    """
    if not isinstance(item, dict):
        return str(item) if item else ""
    
    # Handle Bedrock CloudTrail format: input.inputBodyJson.messages[].content[].text
    if 'input' in item:
        input_data = item['input']
        if isinstance(input_data, dict):
            # Check for inputBodyJson
            if 'inputBodyJson' in input_data:
                input_body = input_data['inputBodyJson']
                if isinstance(input_body, dict) and 'messages' in input_body:
                    messages = input_body['messages']
                    if isinstance(messages, list):
                        # Combine all user messages
                        user_messages = []
                        for msg in messages:
                            if isinstance(msg, dict) and msg.get('role') == 'user':
                                content = msg.get('content', [])
                                if isinstance(content, list):
                                    for content_item in content:
                                        if isinstance(content_item, dict) and 'text' in content_item:
                                            text = content_item['text']
                                            if isinstance(text, str) and text.strip():
                                                user_messages.append(text.strip())
                                        elif isinstance(content_item, str) and content_item.strip():
                                            user_messages.append(content_item.strip())
                                elif isinstance(content, str) and content.strip():
                                    user_messages.append(content.strip())
                        
                        if user_messages:
                            # Return ALL user messages combined (this is the full prompt)
                            return "\n\n".join(user_messages)
            
            # Check for direct messages array
            if 'messages' in input_data:
                messages = input_data['messages']
                if isinstance(messages, list):
                    user_messages = []
                    for msg in messages:
                        if isinstance(msg, dict) and msg.get('role') == 'user':
                            content = msg.get('content', [])
                            if isinstance(content, list):
                                for content_item in content:
                                    if isinstance(content_item, dict) and 'text' in content_item:
                                        text = content_item['text']
                                        if isinstance(text, str) and text.strip():
                                            user_messages.append(text.strip())
                                    elif isinstance(content_item, str) and content_item.strip():
                                        user_messages.append(content_item.strip())
                            elif isinstance(content, str) and content.strip():
                                user_messages.append(content.strip())
                    
                    if user_messages:
                        return "\n\n".join(user_messages)
    
    # Try direct prompt fields
    for field in ['prompt', 'input', 'text', 'question', 'query', 'message']:
        if field in item:
            value = item[field]
            if isinstance(value, str) and len(value.strip()) > 0:
                return value.strip()
            elif isinstance(value, dict):
                # Recursively search in nested dict
                nested = extract_full_prompt_text(value)
                if nested:
                    return nested
    
    return ""


def extract_prompt_from_json_item(item: dict) -> str:
    """
    Extract prompt text from various JSON structures.
    Handles Bedrock CloudTrail format and other common formats.
    Specifically handles NDJSON files with questions in messages.
    This version tries to extract individual questions if found.
    """
    if not isinstance(item, dict):
        return str(item) if item else ""
    
    # Try direct prompt fields first
    for field in ['prompt', 'input', 'text', 'question', 'query', 'message']:
        if field in item:
            value = item[field]
            if isinstance(value, str) and len(value.strip()) > 0:
                return value.strip()
            elif isinstance(value, dict):
                # Recursively search in nested dict
                nested = extract_prompt_from_json_item(value)
                if nested:
                    return nested
    
    # Handle Bedrock CloudTrail format: input.inputBodyJson.messages[].content[].text
    if 'input' in item:
        input_data = item['input']
        if isinstance(input_data, dict):
            # Check for inputBodyJson
            if 'inputBodyJson' in input_data:
                input_body = input_data['inputBodyJson']
                if isinstance(input_body, dict) and 'messages' in input_body:
                    messages = input_body['messages']
                    if isinstance(messages, list):
                        # Combine all user messages
                        user_messages = []
                        for msg in messages:
                            if isinstance(msg, dict) and msg.get('role') == 'user':
                                content = msg.get('content', [])
                                if isinstance(content, list):
                                    for content_item in content:
                                        if isinstance(content_item, dict) and 'text' in content_item:
                                            text = content_item['text']
                                            if isinstance(text, str) and text.strip():
                                                # Try to extract questions from "Questions:" section
                                                questions_text = _extract_questions_from_text(text)
                                                if questions_text:
                                                    return questions_text
                                                user_messages.append(text.strip())
                                        elif isinstance(content_item, str) and content_item.strip():
                                            questions_text = _extract_questions_from_text(content_item)
                                            if questions_text:
                                                return questions_text
                                            user_messages.append(content_item.strip())
                                elif isinstance(content, str) and content.strip():
                                    questions_text = _extract_questions_from_text(content)
                                    if questions_text:
                                        return questions_text
                                    user_messages.append(content.strip())
                        
                        if user_messages:
                            # Return the last user message (usually contains the actual question)
                            return user_messages[-1] if len(user_messages) > 0 else "\n\n".join(user_messages)
            
            # Check for direct messages array
            if 'messages' in input_data:
                messages = input_data['messages']
                if isinstance(messages, list):
                    user_messages = []
                    for msg in messages:
                        if isinstance(msg, dict) and msg.get('role') == 'user':
                            content = msg.get('content', [])
                            if isinstance(content, list):
                                for content_item in content:
                                    if isinstance(content_item, dict) and 'text' in content_item:
                                        text = content_item['text']
                                        if isinstance(text, str) and text.strip():
                                            questions_text = _extract_questions_from_text(text)
                                            if questions_text:
                                                return questions_text
                                            user_messages.append(text.strip())
                                    elif isinstance(content_item, str) and content_item.strip():
                                        questions_text = _extract_questions_from_text(content_item)
                                        if questions_text:
                                            return questions_text
                                        user_messages.append(content_item.strip())
                            elif isinstance(content, str) and content.strip():
                                questions_text = _extract_questions_from_text(content)
                                if questions_text:
                                    return questions_text
                                user_messages.append(content.strip())
                    
                    if user_messages:
                        return user_messages[-1] if len(user_messages) > 0 else "\n\n".join(user_messages)
    
    # Try to find any string value that looks like a prompt (longer than 20 chars, not a timestamp)
    for key, value in item.items():
        if isinstance(value, str) and len(value.strip()) > 20:
            # Skip timestamps and IDs
            if not (key.lower() in ['timestamp', 'time', 'id', 'requestid', 'date'] or 
                    value.strip().startswith('202') or  # Dates like 2025-10-01
                    len(value.strip().split()) < 3):  # Too short
                questions_text = _extract_questions_from_text(value)
                if questions_text:
                    return questions_text
                return value.strip()
    
    # Last resort: try to extract from any nested structures
    for key, value in item.items():
        if isinstance(value, dict):
            nested = extract_prompt_from_json_item(value)
            if nested:
                return nested
        elif isinstance(value, list) and len(value) > 0:
            # Check first item in list
            if isinstance(value[0], dict):
                nested = extract_prompt_from_json_item(value[0])
                if nested:
                    return nested
    
    return ""


def _extract_questions_from_text(text: str) -> str:
    """
    Extract questions from text that contains a "Questions:" section with JSON array.
    Returns formatted questions or empty string if not found.
    """
    if not isinstance(text, str):
        return ""
    
    # Look for "Questions:" section (case-insensitive)
    questions_marker = "Questions:"
    questions_marker_lower = questions_marker.lower()
    text_lower = text.lower()
    
    if questions_marker_lower in text_lower:
        # Find the start of the questions array (case-insensitive search)
        start_idx = text_lower.find(questions_marker_lower)
        if start_idx >= 0:
            # Find the actual marker in original text (preserve case)
            actual_marker = text[start_idx:start_idx + len(questions_marker)]
            after_marker = text[start_idx + len(questions_marker):].strip()
            
            # Try to find the JSON array
            # Look for opening bracket
            bracket_start = after_marker.find('[')
            if bracket_start >= 0:
                # Find matching closing bracket (handle nested brackets and CSV double quotes)
                bracket_count = 0
                bracket_end = -1
                in_string = False
                escape_next = False
                # Track if we're in a CSV double-quote sequence (""")
                csv_double_quote = False
                
                i = bracket_start
                while i < len(after_marker):
                    char = after_marker[i]
                    
                    if escape_next:
                        escape_next = False
                        i += 1
                        continue
                    
                    # Check for CSV double quotes (""")
                    if i + 1 < len(after_marker) and char == '"' and after_marker[i+1] == '"':
                        # This is a CSV double quote - toggle string state
                        in_string = not in_string
                        i += 2  # Skip both quotes
                        continue
                    
                    if char == '\\':
                        escape_next = True
                        i += 1
                        continue
                    
                    if char == '"' and not escape_next:
                        in_string = not in_string
                        i += 1
                        continue
                    
                    if not in_string:
                        if char == '[':
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1
                            if bracket_count == 0:
                                bracket_end = i + 1
                                break
                    
                    i += 1
                
                if bracket_end > 0:
                    # Extract the JSON array string
                    json_array_str = after_marker[bracket_start:bracket_end]
                    
                    # Try to parse the JSON array
                    # First, try direct parsing
                    try:
                        questions_array = json.loads(json_array_str)
                        if isinstance(questions_array, list) and len(questions_array) > 0:
                            return _format_questions_from_array(questions_array)
                    except (json.JSONDecodeError, ValueError) as e:
                        # If direct parsing fails, try to handle escaped quotes
                        # The JSON might have escaped quotes like \" or CSV double quotes like ""
                        try:
                            # Handle CSV-style double quotes ("" becomes ")
                            json_array_fixed = json_array_str.replace('""', '"')
                            questions_array = json.loads(json_array_fixed)
                            if isinstance(questions_array, list) and len(questions_array) > 0:
                                return _format_questions_from_array(questions_array)
                        except (json.JSONDecodeError, ValueError):
                            # If that fails, try to extract manually using regex
                            import re
                            # Look for patterns like "Question":"..." or 'Question':'...'
                            # Handle both single and double quotes, and CSV double-escaped quotes
                            
                            # First, try to handle CSV format with double quotes: ""Question"":""...""
                            # We need to match the entire JSON object and extract the Question field
                            question_texts = []
                            
                            # Pattern for CSV format: ""Question"":""...""
                            # Match: ""Question"":"" followed by question text (which may contain escaped quotes) followed by ""
                            csv_pattern = r'""Question""\s*:\s*""((?:[^"]|""|\\"")*)""'
                            csv_matches = re.findall(csv_pattern, json_array_str)
                            for match in csv_matches:
                                # Unescape: "" becomes ", \" becomes "
                                unescaped = match.replace('""', '"').replace('\\""', '"').replace('\\"', '"')
                                unescaped = unescaped.replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
                                if unescaped.strip():
                                    question_texts.append(unescaped.strip())
                            
                            # If no CSV matches, try standard JSON format
                            if not question_texts:
                                question_patterns = [
                                    r'"Question"\s*:\s*"((?:[^"\\]|\\.)*)"',   # Standard: "Question":"..."
                                    r"'Question'\s*:\s*'((?:[^'\\]|\\.)*)'",   # Single quotes
                                    r'"question"\s*:\s*"((?:[^"\\]|\\.)*)"',   # Lowercase
                                    r"'question'\s*:\s*'((?:[^'\\]|\\.)*)'",   # Lowercase single quotes
                                ]
                                
                                for pattern in question_patterns:
                                    matches = re.findall(pattern, json_array_str)
                                    for match in matches:
                                        # Unescape the matched string
                                        unescaped = match.replace('\\"', '"').replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')
                                        if unescaped.strip():
                                            question_texts.append(unescaped.strip())
                            
                            # Remove duplicates while preserving order
                            seen = set()
                            unique_questions = []
                            for q in question_texts:
                                if q not in seen:
                                    seen.add(q)
                                    unique_questions.append(q)
                            
                            if unique_questions:
                                return "\n\n".join([f"Q{i+1}: {q}" for i, q in enumerate(unique_questions)])
    
    # If no questions found, return empty string
    return ""


def _format_questions_from_array(questions_array: list) -> str:
    """Format questions from a parsed JSON array."""
    question_texts = []
    for q_item in questions_array:
        if isinstance(q_item, dict):
            # Try different field names for question (case-insensitive)
            question = None
            for key in ['Question', 'question', 'QuestionText', 'questionText', 'text', 'Text', 'prompt', 'Prompt']:
                if key in q_item:
                    val = q_item[key]
                    if isinstance(val, str) and len(val.strip()) > 0:
                        question = val.strip()
                        break
            
            if not question:
                # Try to find any string value that looks like a question
                for key, val in q_item.items():
                    if isinstance(val, str) and len(val.strip()) > 10:
                        # Skip LinkId and other non-question fields
                        if key.lower() not in ['linkid', 'link_id', 'id', 'link', 'questionid']:
                            question = val.strip()
                            break
            
            if question:
                question_texts.append(question)
        elif isinstance(q_item, str):
            if q_item.strip():
                question_texts.append(q_item.strip())
    
    if question_texts:
        # Return formatted questions
        return "\n\n".join([f"Q{i+1}: {q}" for i, q in enumerate(question_texts)])
    
    return ""

# Page configuration
st.set_page_config(
    page_title="AI Cost Optimizer Pro - Enterprise LLM Analytics",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium CSS Styling
st.markdown("""
<style>
    /* Main Theme */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2.5rem;
        border-radius: 20px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        text-align: center;
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .premium-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%);
        padding: 1.8rem;
        border-radius: 16px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        border: 1px solid rgba(255,255,255,0.3);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
        margin-bottom: 1.5rem;
    }
    
    .premium-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 30px rgba(0,0,0,0.12);
    }
    
    .metric-highlight {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    
    /* Buttons */
    .stButton>button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.75rem 1.5rem;
        font-weight: 600;
        font-size: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
        white-space: normal;
        text-align: center;
        width: 100%;
        word-wrap: break-word;
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    .primary-button {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%) !important;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: rgba(102, 126, 234, 0.1);
        border-radius: 8px 8px 0 0;
        padding: 12px 24px;
        border: 1px solid rgba(102, 126, 234, 0.2);
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* Progress bars */
    .stProgress > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Custom badges */
    .badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        margin: 0.1rem;
    }
    
    .badge-success {
        background: linear-gradient(135deg, #00b09b 0%, #96c93d 100%);
        color: white;
    }
    
    .badge-warning {
        background: linear-gradient(135deg, #f46b45 0%, #eea849 100%);
        color: white;
    }
    
    .badge-info {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Status indicators */
    .status-success {
        color: #00b09b;
        font-weight: 600;
    }
    
    .status-error {
        color: #f46b45;
        font-weight: 600;
    }
    
    /* Custom animations */
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(20px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .fade-in {
        animation: fadeIn 0.6s ease-out;
    }
</style>
""", unsafe_allow_html=True)

# Header with premium design
st.markdown("""
<div class="main-header fade-in">
    <h1 style="color: white; margin: 0; font-size: 3rem;">🚀 AI Cost Optimizer Pro</h1>
    <p style="color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 1.3rem; font-weight: 300;">
        Enterprise-Grade LLM Performance & Cost Analytics
    </p>
    <div style="margin-top: 1rem;">
        <span class="badge badge-success">Real-time Analytics</span>
        <span class="badge badge-warning">Cost Optimization</span>
        <span class="badge badge-info">Multi-Model Comparison</span>
    </div>
</div>
""", unsafe_allow_html=True)

# Initialize session state
if 'evaluation_results' not in st.session_state:
    st.session_state.evaluation_results = []
if 'show_tour' not in st.session_state:
    st.session_state.show_tour = False
if 'uploaded_prompts' not in st.session_state:
    st.session_state.uploaded_prompts = []
if 'uploaded_file_type' not in st.session_state:
    st.session_state.uploaded_file_type = None
if 'selected_models' not in st.session_state:
    st.session_state.selected_models = []
if 'run_evaluation' not in st.session_state:
    st.session_state.run_evaluation = False
if 'prompts_to_evaluate' not in st.session_state:
    st.session_state.prompts_to_evaluate = []
if 'data_reload_key' not in st.session_state:
    st.session_state.data_reload_key = 0

# Set default paths - use absolute paths based on project root
# Get project root directory (parent of src/)
project_root = Path(__file__).parent.parent
config_path = str(project_root / "configs" / "models.yaml")
raw_path = str(project_root / "data" / "runs" / "raw_metrics.csv")
agg_path = str(project_root / "data" / "runs" / "model_comparison.csv")

# Premium Sidebar
with st.sidebar:
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h2 style="color: #667eea; margin-bottom: 0.5rem;">⚙️ Control Panel</h2>
        <p style="color: #666; font-size: 0.9rem;">Test prompts against LLM models</p>
    </div>
    """, unsafe_allow_html=True)
    
    # ==========================================
    # TEST YOUR PROMPT SECTION IN SIDEBAR
    # ==========================================
    st.markdown("""
    <div style="text-align: center; margin-bottom: 1rem;">
        <h2 style="color: #667eea; margin-bottom: 0.5rem;">🧪 Test Your Prompt</h2>
        <p style="color: #666; font-size: 0.9rem;">Test prompts against LLM models</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Prompt Input Section in Sidebar
    with st.expander("📝 Custom Prompt", expanded=True):
        user_prompt = st.text_area(
            "Enter Your Prompt",
            height=100,
            placeholder="Enter your prompt here...",
            help="💡 Tip: Be specific about your expected output format for better analysis.",
            key="custom_prompt_input_sidebar"
        )
    
    # File Upload Section in Sidebar
    with st.expander("📁 Upload File (JSON or CSV)", expanded=False):
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=None,  # Accept all files - we'll validate the content
            accept_multiple_files=False,
            help="Upload a JSON or CSV file containing prompts. CSV should have a 'prompt' column. JSON can be an array of objects with 'prompt' field. Supported extensions: .json, .csv, .txt",
            key="prompt_file_uploader_sidebar"
        )
        
        # Handle file upload
        if uploaded_file is not None:
            # Get file extension with better detection
            file_name = uploaded_file.name.lower()
            file_extension = None
            
            # Check for valid extensions
            if file_name.endswith('.csv'):
                file_extension = 'csv'
            elif file_name.endswith('.json') or file_name.endswith('.jsonl') or file_name.endswith('.ndjson'):
                file_extension = 'json'
            elif file_name.endswith('.txt'):
                # Try to detect if it's JSON or CSV by content
                file_extension = 'txt'
            else:
                # Try to auto-detect by reading first few bytes
                try:
                    peek = uploaded_file.read(100)
                    uploaded_file.seek(0)  # Reset file pointer
                    peek_str = peek.decode('utf-8', errors='ignore') if isinstance(peek, bytes) else str(peek)
                    if peek_str.strip().startswith('[') or peek_str.strip().startswith('{'):
                        file_extension = 'json'
                        st.info("📄 Auto-detected file as JSON format")
                    elif ',' in peek_str and '\n' in peek_str:
                        file_extension = 'csv'
                        st.info("📄 Auto-detected file as CSV format")
                    else:
                        file_extension = 'txt'
                        st.info("📄 Treating file as text format")
                except Exception as e:
                    file_extension = uploaded_file.name.split('.')[-1].lower() if '.' in uploaded_file.name else 'txt'
                    st.warning(f"⚠️ Could not auto-detect file type. Using extension: {file_extension}")
            
            st.session_state.uploaded_file_type = file_extension
            
            try:
                if file_extension == 'csv':
                    df_uploaded = pd.read_csv(uploaded_file)
                    if 'prompt' in df_uploaded.columns:
                        st.session_state.uploaded_prompts = df_uploaded['prompt'].tolist()
                        st.success(f"✅ Loaded {len(st.session_state.uploaded_prompts)} prompts from CSV file")
                        
                        # Initialize selected prompts if not exists
                        if 'selected_uploaded_prompts' not in st.session_state:
                            st.session_state.selected_uploaded_prompts = st.session_state.uploaded_prompts.copy()
                        
                        # Show checkbox list for prompt selection (same as JSON) - moved outside expander to avoid nesting
                        st.markdown("---")
                        st.markdown("### 📋 Select Prompts to Test")
                        st.markdown(f"**Total prompts loaded:** {len(st.session_state.uploaded_prompts)}")
                        
                        # Select all / Deselect all buttons (stacked vertically)
                        if st.button("✅ Select All", key="select_all_csv", use_container_width=True):
                            st.session_state.selected_uploaded_prompts = st.session_state.uploaded_prompts.copy()
                            st.rerun()
                        if st.button("❌ Deselect All", key="deselect_all_csv", use_container_width=True):
                            st.session_state.selected_uploaded_prompts = []
                            st.rerun()
                        
                        st.markdown("---")
                        
                        # Show checkboxes for each prompt
                        selected_prompts = []
                        for idx, prompt in enumerate(st.session_state.uploaded_prompts):
                            # Create a readable preview of the prompt (show first 200 chars)
                            prompt_text = str(prompt).strip()
                            if len(prompt_text) > 200:
                                prompt_preview = prompt_text[:200] + "..."
                            else:
                                prompt_preview = prompt_text
                            
                            # Clean up the preview for display (remove extra whitespace, newlines)
                            prompt_preview = ' '.join(prompt_preview.split())
                            
                            # If prompt is empty or very short, show a default message
                            if not prompt_preview or len(prompt_preview.strip()) < 5:
                                prompt_preview = f"[Empty prompt {idx + 1}]"
                            
                            # Checkbox for each prompt - show the actual prompt text
                            is_selected = st.checkbox(
                                f"**Prompt {idx + 1}:** {prompt_preview}",
                                value=prompt in st.session_state.selected_uploaded_prompts,
                                key=f"csv_prompt_checkbox_{idx}",
                                help=f"Full prompt: {prompt_text[:500] if len(prompt_text) > 500 else prompt_text}"
                            )
                            
                            if is_selected:
                                selected_prompts.append(prompt)
                        
                        # Update session state
                        st.session_state.selected_uploaded_prompts = selected_prompts
                        
                        st.markdown("---")
                        st.info(f"**Selected:** {len(selected_prompts)} / {len(st.session_state.uploaded_prompts)} prompts")
                        
                        # Show preview of selected prompts - use container instead of expander to avoid nesting
                        if selected_prompts:
                            st.markdown("### 👁️ Preview Selected Prompts")
                            for idx, prompt in enumerate(selected_prompts[:5], 1):
                                st.markdown(f"**Prompt {idx}:**")
                                st.text_area(
                                    "",
                                    value=str(prompt)[:500] + ("..." if len(str(prompt)) > 500 else ""),
                                    height=100,
                                    key=f"csv_preview_prompt_{idx}",
                                    disabled=True,
                                    label_visibility="collapsed"
                                )
                            if len(selected_prompts) > 5:
                                st.caption(f"... and {len(selected_prompts) - 5} more prompts")
                    else:
                        st.error("❌ CSV must have 'prompt' column")
                        st.session_state.uploaded_prompts = []
                        st.session_state.selected_uploaded_prompts = []
                        
                elif file_extension == 'json':
                    # Read file content as string (handles both bytes and text)
                    file_content = uploaded_file.read()
                    if isinstance(file_content, bytes):
                        file_content = file_content.decode('utf-8')
                    
                    # Check if this is NDJSON format (one JSON object per line)
                    # First, convert NDJSON to CSV format, then extract questions
                    lines = file_content.strip().split('\n')
                    is_ndjson = len(lines) > 1
                    ndjson_processed = False
                    
                    if is_ndjson:
                        # Try to parse first line as JSON to check if it's NDJSON format
                        try:
                            first_line_json = json.loads(lines[0].strip())
                            if isinstance(first_line_json, dict) and 'input' in first_line_json:
                                # This looks like NDJSON format - convert to CSV first
                                st.info("🔄 Detected NDJSON format. Converting to CSV format...")
                                
                                # Convert NDJSON to CSV format
                                csv_prompts = []
                                prompt_id = 1
                                
                                for line_num, line in enumerate(lines, 1):
                                    line = line.strip()
                                    if not line:
                                        continue
                                    
                                    try:
                                        record = json.loads(line)
                                        if not isinstance(record, dict):
                                            continue
                                        
                                        # Extract FULL prompt text (all user messages combined) for CSV conversion
                                        # Use extract_full_prompt_text to get the complete text, not just questions
                                        extracted_prompt = extract_full_prompt_text(record)
                                        if not extracted_prompt:
                                            continue
                                        
                                        # Detect if JSON is expected - check multiple patterns
                                        extracted_lower = extracted_prompt.lower()
                                        # Check for JSON-related keywords (case-insensitive)
                                        expected_json = (
                                            "json" in extracted_lower or
                                            "return the result in a json" in extracted_lower or
                                            "return the result in a json array" in extracted_lower or
                                            "return the result in json" in extracted_lower or
                                            "return the result in json array" in extracted_lower or
                                            "formatted as follows:" in extracted_lower or
                                            "formatted as follows" in extracted_lower or
                                            ("return" in extracted_lower and "json" in extracted_lower and "array" in extracted_lower) or
                                            ("return" in extracted_lower and "json" in extracted_lower and "formatted" in extracted_lower)
                                        )
                                        
                                        # Extract category
                                        category = "json-gen" if expected_json else "general"
                                        operation = record.get("operation", "")
                                        if operation:
                                            category = operation.lower()
                                        
                                        csv_prompts.append({
                                            "prompt_id": prompt_id,
                                            "prompt": extracted_prompt,
                                            "expected_json": expected_json,
                                            "category": category
                                        })
                                        prompt_id += 1
                                    except json.JSONDecodeError:
                                        continue
                                
                                if csv_prompts:
                                    # Store prompts organized by prompt_id - show full prompt content
                                    st.success(f"✅ Converted {len(csv_prompts)} NDJSON records to CSV format")
                                    
                                    # Store prompts organized by prompt_id
                                    prompts_by_id = {}
                                    all_prompts = []
                                    
                                    for csv_prompt in csv_prompts:
                                        prompt_id = csv_prompt["prompt_id"]
                                        prompt_text = csv_prompt["prompt"]
                                        expected_json = csv_prompt["expected_json"]
                                        category = csv_prompt["category"]
                                        
                                        # Store prompt with its metadata
                                        prompts_by_id[prompt_id] = {
                                            "prompt_id": prompt_id,
                                            "full_prompt": prompt_text,
                                            "expected_json": expected_json,
                                            "category": category
                                        }
                                        all_prompts.append(prompt_text)
                                    
                                    if prompts_by_id:
                                        # Store in session state
                                        st.session_state.prompts_by_id = prompts_by_id
                                        st.session_state.uploaded_prompts = all_prompts
                                        st.success(f"✅ Loaded {len(prompts_by_id)} prompts organized by Prompt ID")
                                        
                                        # Initialize selected prompts if not exists
                                        if 'selected_uploaded_prompts' not in st.session_state:
                                            st.session_state.selected_uploaded_prompts = all_prompts.copy()
                                        
                                        # Show checkbox list for prompt selection organized by prompt_id - moved outside expander to avoid nesting
                                        st.markdown("---")
                                        st.markdown("### 📋 Select Prompts to Test (Organized by Prompt ID)")
                                        st.markdown(f"**Total prompts:** {len(prompts_by_id)}")
                                        
                                        # Select all / Deselect all buttons (side by side)
                                        col1, col2 = st.columns(2)
                                        with col1:
                                            if st.button("✅ Select All", key="select_all_ndjson", use_container_width=True):
                                                st.session_state.selected_uploaded_prompts = all_prompts.copy()
                                                st.rerun()
                                        with col2:
                                            if st.button("❌ Deselect All", key="deselect_all_ndjson", use_container_width=True):
                                                st.session_state.selected_uploaded_prompts = []
                                                st.rerun()
                                        
                                        st.markdown("---")
                                        
                                        # Show prompts organized by prompt_id - use containers instead of nested expanders
                                        selected_prompts = []
                                        for prompt_id in sorted(prompts_by_id.keys()):
                                            prompt_data = prompts_by_id[prompt_id]
                                            full_prompt = prompt_data["full_prompt"]
                                            
                                            # Use container with border instead of expander to avoid nesting
                                            with st.container():
                                                st.markdown(f"#### 📄 Prompt ID {prompt_id}")
                                                
                                                # Checkbox to select this prompt
                                                is_selected = st.checkbox(
                                                    f"**Select Prompt ID {prompt_id}**",
                                                    value=full_prompt in st.session_state.selected_uploaded_prompts,
                                                    key=f"ndjson_prompt_{prompt_id}_checkbox",
                                                    help=f"Select this prompt (ID: {prompt_id}) for testing"
                                                )
                                                
                                                # Show full prompt content in a collapsible checkbox
                                                if st.checkbox(f"📖 View Full Content (Prompt ID {prompt_id})", key=f"view_prompt_{prompt_id}", value=False):
                                                    st.markdown("**Full Prompt Content:**")
                                                    st.text_area(
                                                        "",
                                                        value=full_prompt,
                                                        height=400,
                                                        key=f"prompt_id_{prompt_id}_content",
                                                        disabled=True,
                                                        label_visibility="collapsed"
                                                    )
                                                
                                                if is_selected:
                                                    selected_prompts.append(full_prompt)
                                                    # Store prompt metadata with the prompt for evaluation
                                                    if 'prompt_metadata' not in st.session_state:
                                                        st.session_state.prompt_metadata = {}
                                                    st.session_state.prompt_metadata[full_prompt] = {
                                                        "prompt_id": prompt_id,
                                                        "expected_json": expected_json,
                                                        "category": category
                                                    }
                                                
                                                st.markdown("---")
                                        
                                        st.session_state.selected_uploaded_prompts = selected_prompts
                                        
                                        # Store ALL prompt metadata (not just selected ones) for later use
                                        if 'prompt_metadata' not in st.session_state:
                                            st.session_state.prompt_metadata = {}
                                        # Update metadata for all prompts in prompts_by_id
                                        for pid, pdata in prompts_by_id.items():
                                            full_prompt_text = pdata["full_prompt"]
                                            st.session_state.prompt_metadata[full_prompt_text] = {
                                                "prompt_id": pdata["prompt_id"],
                                                "expected_json": pdata["expected_json"],
                                                "category": pdata["category"]
                                            }
                                        
                                        st.info(f"**Selected:** {len(selected_prompts)} / {len(prompts_by_id)} prompts")
                                        if len(selected_prompts) > 0 and len(selected_prompts) <= 5:
                                            st.caption("**Selected prompts:**")
                                            for i, prompt_id in enumerate(sorted(prompts_by_id.keys()), 1):
                                                if prompts_by_id[prompt_id]["full_prompt"] in selected_prompts:
                                                    st.caption(f"Prompt ID {prompt_id}")
                                        elif len(selected_prompts) > 5:
                                            st.caption(f"**Selected {len(selected_prompts)} prompts**")
                                    else:
                                        st.warning("⚠️ No questions found in the converted CSV prompts. Displaying full prompts instead.")
                                        # Fall back to showing full prompts
                                        st.session_state.uploaded_prompts = [p["prompt"] for p in csv_prompts]
                                        if 'selected_uploaded_prompts' not in st.session_state:
                                            st.session_state.selected_uploaded_prompts = st.session_state.uploaded_prompts.copy()
                                else:
                                    st.error("❌ Could not extract prompts from NDJSON file")
                                    st.session_state.uploaded_prompts = []
                                
                                # Mark that NDJSON was processed
                                ndjson_processed = True
                        except (json.JSONDecodeError, ValueError, KeyError):
                            # Not NDJSON or error parsing, continue with regular JSON processing
                            pass
                    
                    # Only process as regular JSON if NDJSON was not processed
                    if not ndjson_processed:
                        # Try to parse as regular JSON first
                        data = None
                        json_error = None
                        
                        try:
                            # Try parsing as single JSON object/array
                            is_valid, parsed = is_valid_json(file_content)
                            if is_valid:
                                data = parsed
                        except Exception as e:
                            json_error = str(e)
                        
                        # If JSON parsing failed or has "Extra data" error, try JSONL format
                        if data is None or (json_error and "Extra data" in json_error):
                            # Try parsing as JSONL (one JSON object per line)
                            try:
                                lines = file_content.strip().split('\n')
                                jsonl_objects = []
                                for line_num, line in enumerate(lines, 1):
                                    line = line.strip()
                                    if not line:
                                        continue
                                    
                                    is_valid, parsed = is_valid_json(line)
                                    if is_valid:
                                        jsonl_objects.append(parsed)
                                    else:
                                        # If one line fails, might not be JSONL
                                        break
                                
                                # If we successfully parsed multiple lines as JSON, it's JSONL
                                if len(jsonl_objects) > 0:
                                    data = jsonl_objects
                                elif data is None:
                                    # If JSONL also failed, try to parse just the first valid JSON object
                                    # This handles cases where there's extra data after the main JSON
                                    try:
                                        # Find the first complete JSON object
                                        first_obj_end = file_content.find('\n')
                                        if first_obj_end > 0:
                                            first_line = file_content[:first_obj_end].strip()
                                            is_valid, parsed = is_valid_json(first_line)
                                            if is_valid:
                                                data = [parsed]  # Wrap in list for consistency
                                    except:
                                        pass
                            except Exception as e:
                                pass
                        
                        # If still no data, show error
                        if data is None:
                            st.error(f"❌ Error parsing JSON file: {json_error or 'Invalid JSON format. Please ensure the file is valid JSON or JSONL format.'}")
                            st.session_state.uploaded_prompts = []
                        else:
                            # Handle different JSON structures
                            prompts = []
                            
                            # Helper function to split multiple questions into individual prompts
                            def add_prompts_with_splitting(extracted_text):
                                """Add prompts, splitting multiple questions if needed."""
                                if "\n\nQ" in extracted_text and extracted_text.count("Q") > 1:
                                    # Split by question markers to get individual questions
                                    question_parts = extracted_text.split("\n\nQ")
                                    for i, part in enumerate(question_parts):
                                        if part.strip():
                                            if i == 0 and not part.startswith("Q"):
                                                # First part might not have Q prefix
                                                prompts.append(part.strip())
                                            else:
                                                prompts.append(f"Q{part.strip()}")
                                else:
                                    prompts.append(extracted_text)
                            
                            # If data is a list (from JSON array or JSONL)
                            if isinstance(data, list):
                                for item in data:
                                    if isinstance(item, dict):
                                        # Use comprehensive extraction function
                                        extracted_prompt = extract_prompt_from_json_item(item)
                                        if extracted_prompt:
                                            add_prompts_with_splitting(extracted_prompt)
                                        else:
                                            # Fallback: try to stringify the whole item
                                            prompts.append(str(item))
                                    elif isinstance(item, str):
                                        prompts.append(item)
                            
                            # If data is a single dict
                            elif isinstance(data, dict):
                                if 'prompts' in data:
                                    prompt_list = data['prompts']
                                    if isinstance(prompt_list, list):
                                        # Extract prompts from each item in the list
                                        for item in prompt_list:
                                            if isinstance(item, dict):
                                                extracted = extract_prompt_from_json_item(item)
                                                if extracted:
                                                    add_prompts_with_splitting(extracted)
                                            elif isinstance(item, str):
                                                prompts.append(item)
                                    else:
                                        if isinstance(prompt_list, dict):
                                            extracted = extract_prompt_from_json_item(prompt_list)
                                        else:
                                            extracted = str(prompt_list)
                                        if extracted:
                                            add_prompts_with_splitting(extracted)
                                else:
                                    # Try to extract prompt from the dict
                                    extracted_prompt = extract_prompt_from_json_item(data)
                                    if extracted_prompt:
                                        add_prompts_with_splitting(extracted_prompt)
                                    else:
                                        st.error("❌ Could not extract prompt from JSON. Please ensure the JSON contains a 'prompt', 'input', or 'messages' field.")
                                        st.session_state.uploaded_prompts = []
                                        prompts = []
                            
                            st.session_state.uploaded_prompts = prompts
                            
                            if st.session_state.uploaded_prompts:
                                st.success(f"✅ Loaded {len(st.session_state.uploaded_prompts)} prompts from JSON/JSONL file")
                                
                                # Initialize selected prompts if not exists
                                if 'selected_uploaded_prompts' not in st.session_state:
                                    st.session_state.selected_uploaded_prompts = st.session_state.uploaded_prompts.copy()
                                
                                # Show checkbox list for prompt selection - moved outside expander to avoid nesting
                                st.markdown("---")
                                st.markdown("### 📋 Select Prompts to Test")
                                st.markdown(f"**Total prompts loaded:** {len(st.session_state.uploaded_prompts)}")
                                
                                # Select all / Deselect all buttons (stacked vertically)
                                if st.button("✅ Select All", key="select_all_uploaded", use_container_width=True):
                                    st.session_state.selected_uploaded_prompts = st.session_state.uploaded_prompts.copy()
                                    st.rerun()
                                if st.button("❌ Deselect All", key="deselect_all_uploaded", use_container_width=True):
                                    st.session_state.selected_uploaded_prompts = []
                                    st.rerun()
                                
                                st.markdown("---")
                                
                                # Show checkboxes for each prompt
                                selected_prompts = []
                                for idx, prompt in enumerate(st.session_state.uploaded_prompts):
                                    # Create a readable preview of the prompt (show first 200 chars)
                                    prompt_text = str(prompt).strip()
                                    if len(prompt_text) > 200:
                                        prompt_preview = prompt_text[:200] + "..."
                                    else:
                                        prompt_preview = prompt_text
                                    
                                    # Clean up the preview for display (remove extra whitespace, newlines)
                                    prompt_preview = ' '.join(prompt_preview.split())
                                    
                                    # If prompt is empty or very short, show a default message
                                    if not prompt_preview or len(prompt_preview.strip()) < 5:
                                        prompt_preview = f"[Empty prompt {idx + 1}]"
                                    
                                    # Checkbox for each prompt - show the actual prompt text
                                    is_selected = st.checkbox(
                                        f"**Prompt {idx + 1}:** {prompt_preview}",
                                        value=prompt in st.session_state.selected_uploaded_prompts,
                                        key=f"prompt_checkbox_{idx}",
                                        help=f"Full prompt: {prompt_text[:500] if len(prompt_text) > 500 else prompt_text}"
                                    )
                                    
                                    if is_selected:
                                        selected_prompts.append(prompt)
                                
                                # Update session state
                                st.session_state.selected_uploaded_prompts = selected_prompts
                                
                                st.markdown("---")
                                st.info(f"**Selected:** {len(selected_prompts)} / {len(st.session_state.uploaded_prompts)} prompts")
                                
                                # Show preview of selected prompts - use container instead of expander to avoid nesting
                                if selected_prompts:
                                    st.markdown("### 👁️ Preview Selected Prompts")
                                    for idx, prompt in enumerate(selected_prompts[:5], 1):
                                        st.markdown(f"**Prompt {idx}:**")
                                        st.text_area(
                                            "",
                                            value=prompt[:500] + ("..." if len(prompt) > 500 else ""),
                                            height=100,
                                            key=f"preview_prompt_{idx}",
                                            disabled=True,
                                            label_visibility="collapsed"
                                        )
                                    if len(selected_prompts) > 5:
                                        st.caption(f"... and {len(selected_prompts) - 5} more prompts")
                            
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.session_state.uploaded_prompts = []
        else:
            st.session_state.uploaded_prompts = []
            st.session_state.selected_uploaded_prompts = []
            st.session_state.uploaded_file_type = None
    
    # ==========================================
    # CLOUDWATCH LOG UPLOAD SECTION
    # ==========================================
    st.markdown("---")
    with st.expander("☁️ Upload CloudWatch Logs", expanded=False):
        st.markdown("""
        <div style="margin-bottom: 1rem;">
            <p style="color: #666; font-size: 0.9rem;">
                Upload AWS CloudWatch logs to extract and analyze Bedrock model metrics.
                Supports JSON lines (NDJSON) or JSON array format.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        cloudwatch_file = st.file_uploader(
            "Upload CloudWatch Log File",
            type=None,  # Accept all files - we'll validate the content
            accept_multiple_files=False,
            help="Upload CloudWatch logs in JSON lines (NDJSON) or JSON array format. Supported extensions: .json, .txt, .log, or any text file.",
            key="cloudwatch_file_uploader"
        )
        
        if cloudwatch_file is not None:
            try:
                # Read file content
                # Validate file extension
                file_name = cloudwatch_file.name.lower()
                valid_extensions = ['.json', '.txt', '.log', '.jsonl', '.ndjson']
                file_ext = None
                for ext in valid_extensions:
                    if file_name.endswith(ext):
                        file_ext = ext
                        break
                
                if file_ext is None:
                    st.warning(f"⚠️ File extension not recognized. Expected: {', '.join(valid_extensions)}. Proceeding anyway...")
                
                # Read file content (handle large files)
                try:
                    # For large files, read in chunks if needed
                    file_content = cloudwatch_file.read()
                    if isinstance(file_content, bytes):
                        try:
                            file_content = file_content.decode('utf-8')
                        except UnicodeDecodeError:
                            # Try with error handling
                            file_content = file_content.decode('utf-8', errors='ignore')
                            st.warning("⚠️ Some characters could not be decoded. File processed with error handling.")
                except Exception as e:
                    st.error(f"❌ Error reading file: {str(e)}")
                    st.stop()
                
                if not file_content or len(file_content.strip()) == 0:
                    st.error("❌ File is empty or could not be read.")
                    st.stop()
                
                # Load model registry for parsing
                try:
                    config_file = Path(config_path)
                    if config_file.exists():
                        cw_registry = ModelRegistry(config_path)
                    else:
                        cw_registry = None
                        st.warning("⚠️ Model registry not found. Some features may be limited.")
                except Exception as e:
                    cw_registry = None
                    st.warning(f"⚠️ Could not load model registry: {e}")
                
                # Parse CloudWatch logs
                with st.spinner("📊 Parsing CloudWatch logs... This may take a moment for large files."):
                    parser = CloudWatchParser(cw_registry)
                    
                    # Show file info
                    file_size_mb = len(file_content.encode('utf-8')) / (1024 * 1024)
                    total_lines = len([l for l in file_content.split('\n') if l.strip()])
                    st.info(f"📄 **File:** {cloudwatch_file.name} | **Size:** {file_size_mb:.2f} MB | **Lines:** {total_lines:,}")
                    
                    # Parse the file
                    metrics = parser.parse_log_file(file_content)
                    
                    # Show parsing progress
                    if total_lines > 1000:
                        st.info(f"✅ Processed {total_lines:,} log lines")
                
                if metrics:
                    st.success(f"✅ Successfully parsed {len(metrics)} log entries")
                    
                    # Show summary
                    metrics_df = pd.DataFrame(metrics)
                    summary_col1, summary_col2, summary_col3 = st.columns(3)
                    
                    with summary_col1:
                        st.metric("Total Entries", len(metrics))
                    
                    with summary_col2:
                        success_count = len(metrics_df[metrics_df['status'] == 'success']) if 'status' in metrics_df.columns else 0
                        st.metric("Successful", success_count)
                    
                    with summary_col3:
                        unique_models = metrics_df['model_name'].nunique() if 'model_name' in metrics_df.columns else 0
                        st.metric("Models Found", unique_models)
                    
                    # Extract unique prompts from parsed metrics
                    cloudwatch_prompts = []
                    cloudwatch_prompt_metadata = {}
                    
                    # Debug: Check what fields are available in metrics
                    if metrics:
                        sample_metric = metrics[0]
                        with st.expander("🔍 Debug: Sample Metric Fields", expanded=False):
                            st.json({k: str(v)[:200] if isinstance(v, str) and len(str(v)) > 200 else v for k, v in sample_metric.items()})
                    
                    for metric in metrics:
                        # Try multiple field names for prompt (parser uses 'input_prompt')
                        prompt = None
                        for field in ['input_prompt', 'prompt', 'input', 'message', 'text']:
                            if field in metric:
                                prompt_value = metric.get(field, '')
                                if prompt_value:
                                    # Handle both string and None values
                                    if isinstance(prompt_value, str):
                                        prompt_value = prompt_value.strip()
                                    else:
                                        prompt_value = str(prompt_value).strip()
                                    if prompt_value:
                                        prompt = prompt_value
                                        break
                        
                        # If still no prompt, try to extract from nested structures
                        if not prompt:
                            # Check if there's a nested prompt structure
                            if 'request' in metric:
                                request = metric['request']
                                if isinstance(request, dict):
                                    for field in ['prompt', 'input', 'messages', 'inputText']:
                                        if field in request:
                                            prompt_value = request[field]
                                            if isinstance(prompt_value, str):
                                                prompt = prompt_value.strip()
                                            elif isinstance(prompt_value, list) and prompt_value:
                                                # Extract from messages array
                                                for msg in prompt_value:
                                                    if isinstance(msg, dict):
                                                        if 'content' in msg:
                                                            content = msg['content']
                                                            if isinstance(content, str):
                                                                prompt = content.strip()
                                                            elif isinstance(content, list):
                                                                for item in content:
                                                                    if isinstance(item, dict) and 'text' in item:
                                                                        prompt = item['text'].strip()
                                                                    elif isinstance(item, str):
                                                                        prompt = item.strip()
                                                                    if prompt:
                                                                        break
                                                        elif 'text' in msg:
                                                            prompt = msg['text'].strip()
                                                    if prompt:
                                                        break
                                            if prompt:
                                                break
                        
                        if prompt and prompt not in cloudwatch_prompts:
                            cloudwatch_prompts.append(prompt)
                            # Store metadata for each prompt
                            cloudwatch_prompt_metadata[prompt] = {
                                'model_name': metric.get('model_name', 'Unknown'),
                                'timestamp': metric.get('timestamp', ''),
                                'status': metric.get('status', 'unknown'),
                                'source': 'cloudwatch'
                            }
                    
                    # Store in session state for later use
                    st.session_state.cloudwatch_prompts = cloudwatch_prompts
                    st.session_state.cloudwatch_prompt_metadata = cloudwatch_prompt_metadata
                    
                    # Show prompt selection section (always show, even if empty)
                    st.markdown("---")
                    st.markdown("### 📝 Select Prompts from CloudWatch Logs")
                    
                    if cloudwatch_prompts:
                        st.info(f"**Found {len(cloudwatch_prompts)} unique prompts** in the CloudWatch logs. Select prompts to test with your models.")
                        
                        # Initialize selected CloudWatch prompts if not exists
                        if 'selected_cloudwatch_prompts' not in st.session_state:
                            st.session_state.selected_cloudwatch_prompts = []
                        
                        # Select all / Deselect all buttons
                        cw_col1, cw_col2 = st.columns(2)
                        with cw_col1:
                            if st.button("✅ Select All CloudWatch Prompts", key="select_all_cw", use_container_width=True):
                                st.session_state.selected_cloudwatch_prompts = cloudwatch_prompts.copy()
                                st.rerun()
                        with cw_col2:
                            if st.button("❌ Deselect All", key="deselect_all_cw", use_container_width=True):
                                st.session_state.selected_cloudwatch_prompts = []
                                st.rerun()
                        
                        st.markdown("---")
                        
                        # Show checkboxes for each prompt
                        selected_cw_prompts = []
                        for idx, prompt in enumerate(cloudwatch_prompts):
                            # Get metadata for this prompt
                            meta = cloudwatch_prompt_metadata.get(prompt, {})
                            model_name = meta.get('model_name', 'Unknown')
                            
                            # Create a readable preview
                            prompt_text = str(prompt).strip()
                            if len(prompt_text) > 150:
                                prompt_preview = prompt_text[:150] + "..."
                            else:
                                prompt_preview = prompt_text
                            
                            # Clean up preview
                            prompt_preview = ' '.join(prompt_preview.split())
                            
                            # Checkbox with model info
                            is_selected = st.checkbox(
                                f"**Prompt {idx + 1}** (from {model_name}): {prompt_preview}",
                                value=prompt in st.session_state.selected_cloudwatch_prompts,
                                key=f"cw_prompt_checkbox_{idx}",
                                help=f"Full prompt: {prompt_text[:500] if len(prompt_text) > 500 else prompt_text}"
                            )
                            
                            if is_selected:
                                selected_cw_prompts.append(prompt)
                        
                        # Update session state
                        st.session_state.selected_cloudwatch_prompts = selected_cw_prompts
                        
                        st.markdown("---")
                        st.success(f"**✅ Selected {len(selected_cw_prompts)} prompt(s) from CloudWatch logs**")
                        st.info("💡 These prompts will be available for evaluation. Go to the sidebar to run evaluations with selected prompts.")
                        
                        # Show preview of selected prompts
                        if selected_cw_prompts:
                            with st.expander(f"👁️ Preview Selected CloudWatch Prompts ({len(selected_cw_prompts)})", expanded=False):
                                for idx, prompt in enumerate(selected_cw_prompts[:5], 1):
                                    meta = cloudwatch_prompt_metadata.get(prompt, {})
                                    st.markdown(f"**Prompt {idx}** (from {meta.get('model_name', 'Unknown')}):")
                                    st.text_area(
                                        "",
                                        value=prompt[:1000] + ("..." if len(prompt) > 1000 else ""),
                                        height=150,
                                        key=f"preview_cw_prompt_{idx}",
                                        disabled=True,
                                        label_visibility="collapsed"
                                    )
                                if len(selected_cw_prompts) > 5:
                                    st.caption(f"... and {len(selected_cw_prompts) - 5} more prompts")
                    else:
                        st.warning("⚠️ **No prompts found** in the parsed CloudWatch logs.")
                        st.info("""
                        **Possible reasons:**
                        - The log entries don't contain extractable prompt text
                        - Prompts might be in a format that couldn't be parsed
                        - Check the "Debug: Sample Metric Fields" expander above to see what fields are available
                        
                        **Note:** The metrics were still saved successfully. You can use custom prompts or upload prompts from a file instead.
                        """)
                    
                    # Show preview
                    st.markdown("---")
                    if st.checkbox("Show Metrics Preview", key="cw_preview_checkbox"):
                        st.dataframe(metrics_df[['model_name', 'status', 'latency_ms', 'input_tokens', 'output_tokens', 'cost_usd_total']].head(10))
                    
                    # Save to metrics file
                    if st.button("💾 Save to Metrics Database", key="save_cloudwatch_metrics", use_container_width=True):
                        try:
                            # Get output directory from session state or use default
                            output_dir = st.session_state.get('output_dir', 'data/runs')
                            metrics_logger = MetricsLogger(output_dir)
                            
                            # Save metrics
                            metrics_logger.log_metrics(metrics)
                            
                            st.success(f"✅ Saved {len(metrics)} metrics to {metrics_logger.raw_csv_path}")
                            
                            # Trigger data reload
                            if 'data_reload_key' in st.session_state:
                                st.session_state.data_reload_key = datetime.now().isoformat()
                            
                            st.info("🔄 Refresh the page to see the new metrics in the dashboard")
                            
                        except Exception as e:
                            st.error(f"❌ Error saving metrics: {str(e)}")
                    
                    # Option to download as CSV
                    csv_data = metrics_df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download Metrics as CSV",
                        data=csv_data,
                        file_name=f"cloudwatch_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        key="download_cw_metrics"
                    )
                    
                else:
                    st.warning("⚠️ No Bedrock metrics found in the uploaded file.")
                    st.info("""
                    **Troubleshooting:**
                    - Ensure the file contains CloudWatch logs with Bedrock API calls
                    - Check that log entries have `logStreamName` containing "bedrock" or `operation` field with "Converse"/"InvokeModel"
                    - Verify the file format is JSON lines (one JSON object per line) or JSON array
                    - Sample log entry should contain fields like: `modelId`, `operation`, `input`, `output`
                    """)
                    
                    # Show sample of first line for debugging
                    if file_content:
                        lines = file_content.strip().split('\n')
                        if lines:
                            try:
                                sample_entry = json.loads(lines[0])
                                with st.expander("🔍 Sample Log Entry (First Line)"):
                                    st.json(sample_entry)
                                    st.caption("Check if this entry contains Bedrock-related fields (modelId, operation, input, output)")
                            except:
                                st.caption(f"First line preview: {lines[0][:200]}...")
                    
            except Exception as e:
                st.error(f"❌ Error parsing CloudWatch logs: {str(e)}")
                import traceback
                with st.expander("Error Details"):
                    st.code(traceback.format_exc())
    
    # Settings Section in Sidebar
    with st.expander("⚙️ Settings", expanded=False):
        expect_json = st.checkbox(
            "Expect JSON Response",
            value=True,
            help="Validate response as JSON and track validity metrics",
            key="expect_json_sidebar"
        )
        
        format_as_json = st.checkbox(
            "Format Prompt as JSON",
            value=False,
            help="Convert the prompt to JSON format before sending to models",
            key="format_as_json_sidebar"
        )
    
    # Model Selection in Sidebar
    st.markdown("### 🤖 Select Models")
    
    # Load model registry here in sidebar
    try:
        config_file = Path(config_path)
        if config_file.exists():
            sidebar_registry = ModelRegistry(config_path)
            available_models = sidebar_registry.list_models()
            if available_models:
                model_options = {model['name']: model for model in available_models}
                selected_model_names = []
                
                for name, model in model_options.items():
                    pricing = sidebar_registry.get_model_pricing(model)
                    pricing_info = f"${pricing['input_per_1k_tokens_usd']:.4f}/1k in, ${pricing['output_per_1k_tokens_usd']:.4f}/1k out"
                    
                    if st.checkbox(f"{name}", key=f"model_sidebar_{name}", help=f"Pricing: {pricing_info}"):
                        selected_model_names.append(name)
                
                st.session_state.selected_models = selected_model_names
            else:
                st.warning("⚠️ No models configured")
                st.session_state.selected_models = []
        else:
            st.warning(f"⚠️ Config file not found: {config_path}")
            st.session_state.selected_models = []
    except Exception as e:
        st.warning(f"⚠️ Error loading models: {str(e)}")
        st.session_state.selected_models = []
    
    # Show CloudWatch prompts status if available
    if st.session_state.get('cloudwatch_prompts'):
        cw_prompts_count = len(st.session_state.cloudwatch_prompts)
        selected_cw_count = len(st.session_state.get('selected_cloudwatch_prompts', []))
        with st.expander("☁️ CloudWatch Prompts Available", expanded=False):
            st.info(f"**{cw_prompts_count} prompts** available from CloudWatch logs")
            if selected_cw_count > 0:
                st.success(f"✅ **{selected_cw_count} selected** for evaluation")
            else:
                st.caption("💡 Go to 'Upload CloudWatch Logs' section to select prompts")
    
    # Input Summary in Sidebar
    prompts_to_use = []
    prompts_with_metadata = []  # Store prompts with their metadata
    
    if user_prompt.strip():
        prompts_to_use.append(user_prompt)
        prompts_with_metadata.append({
            "prompt": user_prompt,
            "expected_json": st.session_state.get('expect_json_sidebar', True),
            "source": "custom"
        })
    
    # Use selected prompts from uploaded file (if any)
    if st.session_state.get('selected_uploaded_prompts'):
        prompt_metadata = st.session_state.get('prompt_metadata', {})
        for prompt in st.session_state.selected_uploaded_prompts:
            prompts_to_use.append(prompt)
            # Get metadata for this prompt if available
            metadata = prompt_metadata.get(prompt, {})
            prompts_with_metadata.append({
                "prompt": prompt,
                "expected_json": metadata.get("expected_json", st.session_state.get('expect_json_sidebar', True)),
                "source": "uploaded",
                "prompt_id": metadata.get("prompt_id")
            })
    
    # Use selected prompts from CloudWatch logs (if any)
    if st.session_state.get('selected_cloudwatch_prompts'):
        cw_prompt_metadata = st.session_state.get('cloudwatch_prompt_metadata', {})
        for prompt in st.session_state.selected_cloudwatch_prompts:
            prompts_to_use.append(prompt)
            # Get metadata for this prompt if available
            metadata = cw_prompt_metadata.get(prompt, {})
            prompts_with_metadata.append({
                "prompt": prompt,
                "expected_json": st.session_state.get('expect_json_sidebar', True),
                "source": "cloudwatch",
                "model_name": metadata.get('model_name'),
                "timestamp": metadata.get('timestamp')
            })
    
    if prompts_to_use:
        custom_count = 1 if user_prompt.strip() else 0
        selected_count = len(st.session_state.get('selected_uploaded_prompts', []))
        cw_count = len(st.session_state.get('selected_cloudwatch_prompts', []))
        st.info(f"**📊 Total Prompts Selected:** {len(prompts_to_use)}")
        if len(prompts_to_use) > 1:
            parts = []
            if custom_count > 0:
                parts.append(f"{custom_count} custom")
            if selected_count > 0:
                parts.append(f"{selected_count} from file")
            if cw_count > 0:
                parts.append(f"{cw_count} from CloudWatch")
            if parts:
                st.caption(f"• {' + '.join(parts)}")
    
    # Run Button in Sidebar
    if st.button("🚀 Run Evaluation", type="primary", use_container_width=True, key="run_eval_sidebar"):
        st.session_state.run_evaluation = True
        st.session_state.prompts_to_evaluate = prompts_to_use
        st.session_state.prompts_with_metadata = prompts_with_metadata  # Store metadata
        st.rerun()
    
    # Support Section
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 1rem;">
        <p style="color: #666; font-size: 0.8rem;">Need help?</p>
        <p style="color: #667eea; font-size: 0.9rem; font-weight: 600;">support@aicostoptimizer.com</p>
    </div>
    """, unsafe_allow_html=True)

# Load data functions with cache key for syncing
@st.cache_data
def load_data(raw_path: str, agg_path: str, cache_key: int = 0):
    """Load and cache data files with enhanced error handling.
    cache_key allows cache invalidation when new data is saved."""
    raw_df = pd.DataFrame()
    agg_df = pd.DataFrame()
    
    try:
        if Path(raw_path).exists():
            # Read CSV with proper handling of multi-line fields
            try:
                raw_df = pd.read_csv(
                    raw_path,
                    quoting=1,  # QUOTE_ALL
                    escapechar=None,
                    doublequote=True,
                    on_bad_lines='skip',  # Skip problematic lines instead of failing
                    engine='python'  # Use Python engine which is more lenient
                )
                # Convert numeric columns to proper numeric types
                numeric_columns = ['input_tokens', 'output_tokens', 'latency_ms', 'cost_usd_input', 'cost_usd_output', 'cost_usd_total']
                for col in numeric_columns:
                    if col in raw_df.columns:
                        raw_df[col] = pd.to_numeric(raw_df[col], errors='coerce')
                # Convert boolean columns
                if 'json_valid' in raw_df.columns:
                    raw_df['json_valid'] = raw_df['json_valid'].astype(str).replace({'True': True, 'False': False, 'true': True, 'false': False, '1': True, '0': False})
                    raw_df['json_valid'] = pd.to_numeric(raw_df['json_valid'], errors='coerce').fillna(0).astype(bool)
            except Exception:
                # If that fails, try with default settings
                try:
                    raw_df = pd.read_csv(raw_path, on_bad_lines='skip', engine='python')
                except Exception:
                    raw_df = pd.DataFrame()
        else:
            pass  # Don't show warning in main sidebar - let it show in sidebar
    except Exception as e:
        pass  # Errors handled in sidebar
    
    try:
        if Path(agg_path).exists():
            try:
                agg_df = pd.read_csv(
                    agg_path,
                    quoting=1,
                    escapechar=None,
                    doublequote=True,
                    on_bad_lines='skip',
                    engine='python'
                )
            except Exception:
                try:
                    agg_df = pd.read_csv(agg_path, on_bad_lines='skip', engine='python')
                except Exception:
                    agg_df = pd.DataFrame()
        else:
            pass
    except Exception as e:
        pass
    
    return raw_df, agg_df

@st.cache_resource(ttl=0)  # Disable caching to ensure fresh config is always loaded
def load_model_registry(config_path: str):
    """Load model registry with enhanced error handling."""
    try:
        config_file = Path(config_path)
        if config_file.exists():
            # Read file modification time to bust cache
            mtime = config_file.stat().st_mtime
            registry = ModelRegistry(config_path)
            return registry, mtime
        else:
            return None, None
    except Exception as e:
        st.error(f"Error loading model registry: {e}")
        return None, None

# Load data and models with cache key for syncing
raw_df, agg_df = load_data(raw_path, agg_path, st.session_state.data_reload_key)
model_registry_result = load_model_registry(config_path)
if model_registry_result:
    model_registry, _ = model_registry_result
else:
    model_registry = None

# Premium Tabs with Icons
tab1, tab2 = st.tabs(["📊 **Overview & Analytics**", "📈 **Historical Results**"])

# ==========================================
# TAB 1: Premium Overview & Analytics
# ==========================================
with tab1:
    # Handle evaluation triggered from sidebar
    if st.session_state.run_evaluation:
        prompts_to_evaluate = st.session_state.prompts_to_evaluate
        prompts_with_metadata = st.session_state.get('prompts_with_metadata', [])
        selected_model_names = st.session_state.selected_models
        expect_json = st.session_state.get('expect_json_sidebar', True)  # Default fallback
        format_as_json = st.session_state.get('format_as_json_sidebar', False)
        
        # Create a mapping of prompt to its metadata for quick lookup
        prompt_metadata_map = {}
        for pm in prompts_with_metadata:
            prompt_metadata_map[pm["prompt"]] = pm
        
        # Get model registry
        model_registry_result = load_model_registry(config_path)
        if model_registry_result:
            model_registry, _ = model_registry_result
        else:
            model_registry = None
        
        if not prompts_to_evaluate:
            st.error("""
            ❌ **Prompt Required**
            
            Please enter a custom prompt or upload a file with prompts in the sidebar.
            """)
            st.session_state.run_evaluation = False
        elif not selected_model_names:
            st.error("""
            ❌ **Models Required**
            
            Please select at least one model in the sidebar.
            """)
            st.session_state.run_evaluation = False
        elif model_registry is None:
            st.error("""
            ❌ **Configuration Required**
            
            Please check your model configuration file path: `{config_path}`
            """.format(config_path=config_path))
            st.session_state.run_evaluation = False
        else:
            # Premium evaluation execution
            with st.status("🚀 **Running Comprehensive Evaluation...**", expanded=True) as status:
                try:
                    evaluator = BedrockEvaluator(model_registry)
                    selected_models = [model_registry.get_model_by_name(name) for name in selected_model_names]
                    
                    status.update(label="🔄 Initializing evaluation engine...")
                    time.sleep(0.5)
                    
                    results = []
                    progress_bar = st.progress(0)
                    total_evaluations = len(prompts_to_evaluate) * len(selected_models)
                    current_evaluation = 0
                    
                    for prompt_idx, current_prompt in enumerate(prompts_to_evaluate):
                        # Get metadata for this prompt if available
                        prompt_meta = prompt_metadata_map.get(current_prompt, {})
                        prompt_expected_json = prompt_meta.get("expected_json", expect_json)
                        prompt_prompt_id = prompt_meta.get("prompt_id", f"prompt_{prompt_idx+1}" if len(prompts_to_evaluate) > 1 else None)
                        
                        for model_idx, model in enumerate(selected_models):
                            if model is None:
                                continue
                            
                            current_evaluation += 1
                            status.update(label=f"🧪 Testing {model['name']} with prompt {prompt_idx+1}/{len(prompts_to_evaluate)}... ({current_evaluation}/{total_evaluations})")
                            progress_bar.progress(current_evaluation / total_evaluations)
                            
                            try:
                                # Format prompt as JSON if requested
                                final_prompt = current_prompt
                                if format_as_json:
                                    try:
                                        json.loads(current_prompt)
                                        final_prompt = current_prompt
                                    except (json.JSONDecodeError, ValueError):
                                        prompt_json = {
                                            "prompt": current_prompt,
                                            "instruction": "Please respond to the following prompt. If JSON format is requested, return your answer as valid JSON."
                                        }
                                        final_prompt = json.dumps(prompt_json, indent=2)
                                else:
                                    # Use prompt-specific expected_json, not the global setting
                                    if prompt_expected_json:
                                        final_prompt = f"{current_prompt}\n\nPlease respond in valid JSON format."
                                
                                metrics = evaluator.evaluate_prompt(
                                    prompt=final_prompt,
                                    model=model,
                                    prompt_id=prompt_prompt_id,
                                    expected_json=prompt_expected_json,  # Use prompt-specific expected_json
                                    run_id=f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                                )
                                results.append(metrics)
                            
                            except Exception as e:
                                error_metric = {
                                    "timestamp": datetime.utcnow().isoformat() + "Z",
                                    "run_id": f"dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                                    "model_name": model.get("name", "unknown"),
                                    "model_id": model.get("bedrock_model_id", "unknown"),
                                    "prompt_id": f"prompt_{prompt_idx+1}" if len(prompts_to_evaluate) > 1 else None,
                                    "input_prompt": final_prompt,  # Store input prompt even for errors
                                    "input_tokens": 0,
                                    "output_tokens": 0,
                                    "latency_ms": 0,
                                    "json_valid": False,
                                    "error": str(e),
                                    "status": "error",
                                    "cost_usd_input": 0.0,
                                    "cost_usd_output": 0.0,
                                    "cost_usd_total": 0.0,
                                    "response": ""
                                }
                                results.append(error_metric)
                    
                    progress_bar.progress(1.0)
                    status.update(label="✅ Evaluation complete! Generating insights...", state="complete")
                    
                except Exception as e:
                    status.update(label="❌ Evaluation failed", state="error")
                    st.error(f"Evaluation error: {e}")
            
            # Save results automatically and reload data
            if results:
                try:
                    # Use absolute path based on project root
                    project_root = Path(__file__).parent.parent
                    data_runs_dir = project_root / "data" / "runs"
                    data_runs_dir.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
                    
                    metrics_logger = MetricsLogger(data_runs_dir)
                    metrics_logger.log_metrics(results)
                    
                    # Regenerate aggregated report to ensure all graphs are synced
                    report_generator = ReportGenerator(data_runs_dir)
                    report_generator.generate_report()
                    
                    st.session_state.evaluation_results = results
                    # Increment cache key to force data reload and sync all graphs
                    st.session_state.data_reload_key += 1
                    st.cache_data.clear()
                    # Reload data with new cache key to ensure all components see fresh data
                    raw_df, agg_df = load_data(raw_path, agg_path, st.session_state.data_reload_key)
                    
                    # Reset evaluation flag after processing
                    st.session_state.run_evaluation = False
                    
                    # Force page refresh to update all graphs with new data
                    st.success("✅ **Evaluation Complete!** Results saved and dashboard updated. Refreshing graphs...")
                    st.rerun()  # Refresh the page to show updated graphs
                except Exception as e:
                    st.error(f"❌ Error saving results: {e}")
                    st.session_state.evaluation_results = results
                    # Reset evaluation flag even on error
                    st.session_state.run_evaluation = False
    
    # Always reload data with current cache key to ensure sync
    raw_df, agg_df = load_data(raw_path, agg_path, st.session_state.data_reload_key)
    
    # Show evaluation results summary if available
    if st.session_state.get('evaluation_results'):
        results = st.session_state.evaluation_results
        success_count = len([r for r in results if r.get('status') == 'success'])
        
        with st.expander("📊 Latest Evaluation Results", expanded=True):
            st.success(f"🎉 **Evaluation Complete!** {success_count} successful responses.")
            
            # Quick evaluation summary
            if results:
                eval_col1, eval_col2, eval_col3, eval_col4 = st.columns(4)
                success_results = [r for r in results if r.get('status') == 'success']
                
                with eval_col1:
                    if success_results:
                        results_df = pd.DataFrame(success_results)
                        # Safely convert to numeric
                        latency_col = pd.to_numeric(results_df.get('latency_ms', pd.Series()), errors='coerce')
                        avg_latency = latency_col.mean() if not latency_col.empty else 0
                        st.metric("⚡ Avg Latency", f"{avg_latency:.0f} ms")
                
                with eval_col2:
                    results_df = pd.DataFrame(results)
                    # Safely convert to numeric
                    cost_col = pd.to_numeric(results_df.get('cost_usd_total', pd.Series()), errors='coerce')
                    total_cost = cost_col.sum() if not cost_col.empty else 0
                    st.metric("💰 Total Cost", f"${total_cost:.6f}")
                
                with eval_col3:
                    if success_results:
                        valid_count = len([r for r in success_results if r.get('json_valid', False)])
                        validity_pct = (valid_count / len(success_results) * 100) if success_results else 0
                        st.metric("✅ JSON Validity", f"{validity_pct:.1f}%")
                
                with eval_col4:
                    if success_results:
                        results_df = pd.DataFrame(success_results)
                        # Safely convert to numeric
                        input_tokens = pd.to_numeric(results_df.get('input_tokens', pd.Series()), errors='coerce').fillna(0)
                        output_tokens = pd.to_numeric(results_df.get('output_tokens', pd.Series()), errors='coerce').fillna(0)
                        total_tokens = input_tokens.sum() + output_tokens.sum()
                        st.metric("📝 Total Tokens", f"{int(total_tokens):,}")
            
            # Detailed results table
            st.subheader("📋 Detailed Results")
            results_df = pd.DataFrame(results)
            display_cols = ['model_name', 'latency_ms', 'input_tokens', 'output_tokens', 
                          'cost_usd_total', 'json_valid', 'status']
            if 'error' in results_df.columns:
                display_cols.append('error')
            
            available_cols = [col for col in display_cols if col in results_df.columns]
            display_df = results_df[available_cols].copy()
            
            # Format for display
            if 'latency_ms' in display_df.columns:
                display_df['latency_ms'] = display_df['latency_ms'].apply(lambda x: f"{x:.0f} ms" if pd.notna(x) and x > 0 else "N/A")
            if 'input_tokens' in display_df.columns:
                display_df['input_tokens'] = display_df['input_tokens'].apply(lambda x: f"{x:,}" if pd.notna(x) else "0")
            if 'output_tokens' in display_df.columns:
                display_df['output_tokens'] = display_df['output_tokens'].apply(lambda x: f"{x:,}" if pd.notna(x) else "0")
            if 'cost_usd_total' in display_df.columns:
                display_df['cost_usd_total'] = display_df['cost_usd_total'].apply(lambda x: f"${x:.6f}" if pd.notna(x) and x > 0 else "$0.000000")
            if 'json_valid' in display_df.columns:
                def format_json_valid(x):
                    if pd.isna(x) or x is None:
                        return "➖ N/A"
                    elif x is True:
                        return "✅ Yes"
                    else:
                        return "❌ No"
                display_df['json_valid'] = display_df['json_valid'].apply(format_json_valid)
            if 'status' in display_df.columns:
                display_df['status'] = display_df['status'].apply(lambda x: "✅ Success" if x == "success" else "❌ Error")
            
            st.dataframe(display_df, use_container_width=True, height=200)
        
        # Display JSON Output Responses - moved outside expander to avoid nesting
        if st.session_state.get('evaluation_results'):
            results = st.session_state.evaluation_results
            st.subheader("📄 Output JSON Responses")
            for idx, result in enumerate(results):
                model_name = result.get('model_name', 'Unknown')
                prompt_id = result.get('prompt_id', 'N/A')
                status = result.get('status', 'unknown')
                response = result.get('response', '')
                error = result.get('error', None)
                
                # Create expander title
                if prompt_id and prompt_id != 'N/A':
                    expander_title = f"🔹 {model_name} - {prompt_id}"
                else:
                    expander_title = f"🔹 {model_name}"
                
                if status == 'error':
                    expander_title += " ❌"
                else:
                    expander_title += " ✅"
                
                with st.expander(expander_title, expanded=False):
                    # Display Input Prompt/JSON
                    input_prompt = result.get('input_prompt', '')
                    if input_prompt:
                        st.markdown("### 📥 Input Prompt/JSON")
                        # Try to format as JSON if valid JSON
                        try:
                            input_json_obj = json.loads(input_prompt)
                            st.json(input_json_obj)
                        except (json.JSONDecodeError, ValueError, TypeError):
                            # If not valid JSON, display as text
                            st.code(input_prompt, language='text')
                        
                        st.markdown("---")
                    
                    # Display Output Response/JSON
                    if status == 'success' and response:
                        st.markdown("### 📤 Output Response/JSON")
                        # Try to format as JSON if valid JSON
                        try:
                            json_obj = json.loads(response)
                            st.json(json_obj)
                        except (json.JSONDecodeError, ValueError, TypeError):
                            # If not valid JSON, display as code/text
                            st.markdown("**Response (Text Format):**")
                            st.code(response, language='text')
                        
                        # Show raw response option - use text_area instead of nested expander
                        st.markdown("**📋 Full Raw Output Response:**")
                        st.text_area(
                            "Full Output Response Text",
                            value=response,
                            height=200,
                            key=f"raw_response_{idx}",
                            disabled=True,
                            label_visibility="collapsed"
                        )
                    elif status == 'error':
                        st.markdown("### 📤 Output Response/JSON")
                        st.error(f"**Error:** {error if error else 'Unknown error occurred'}")
                        if response:
                            st.markdown("**Partial Response:**")
                            st.code(response, language='text')
                    else:
                        st.markdown("### 📤 Output Response/JSON")
                        st.warning("No response available")
        
        st.markdown("---")
    
    # Show existing data or empty state - Always show dashboard sections if data exists
    if not (agg_df.empty and raw_df.empty):
        # Get configured models from registry to filter data
        target_models = []
        model_registry_result = load_model_registry(config_path)
        if model_registry_result:
            registry, _ = model_registry_result
            if registry:
                configured_models = registry.list_models()
                target_models = [model['name'] for model in configured_models]
        
        # Clean model names in data (handle tuple format like "('Claude 3 Sonnet',)")
        def clean_model_name(name):
            if pd.isna(name):
                return ""
            name_str = str(name)
            # Remove tuple formatting if present
            if name_str.startswith("('") and name_str.endswith("',)"):
                name_str = name_str[2:-3]  # Remove "('" and "',)"
            elif name_str.startswith("('") and name_str.endswith("')"):
                name_str = name_str[2:-2]  # Remove "('" and "')"
            elif name_str.startswith('("') and name_str.endswith('",)'):
                name_str = name_str[2:-3]  # Remove '("' and '",)'
            return name_str.strip()
        
        # Create a function to match model names - only match configured models
        def matches_target_model(data_model_name, target_models):
            """Check if data model name matches any target model.
            
            Rules:
            - Exact matches always work
            - For Claude: "Claude 3 Sonnet" matches "Claude 3.7 Sonnet" (same major version)
            - For Llama: Must match BOTH version AND size (e.g., "3.2 11B" must match exactly)
            """
            if pd.isna(data_model_name):
                return False
                
            cleaned_data_name = clean_model_name(str(data_model_name)).strip()
            
            for target in target_models:
                target_clean = target.strip()
                
                # 1. Exact match (case-insensitive)
                if cleaned_data_name.lower() == target_clean.lower():
                    return True
                
                # 2. Parse model components
                target_parts = target_clean.split()
                data_parts = cleaned_data_name.split()
                
                if len(target_parts) < 2 or len(data_parts) < 2:
                    continue
                
                # 3. Must have same family (Claude/Llama) and type (Sonnet/Instruct)
                if target_parts[0].lower() != data_parts[0].lower():
                    continue  # Different families
                if target_parts[-1].lower() != data_parts[-1].lower():
                    continue  # Different types
                
                # 4. Claude models: Match only if exact version match OR target has minor version and data has no minor
                # "Claude 3.7 Sonnet" matches "Claude 3 Sonnet" but NOT "Claude 3.5 Sonnet"
                if "claude" in target_clean.lower() and "sonnet" in target_clean.lower():
                    # Extract versions: "Claude 3.7 Sonnet" -> "3.7", "Claude 3 Sonnet" -> "3"
                    target_ver_str = target_parts[1] if len(target_parts) > 1 else ""
                    data_ver_str = data_parts[1] if len(data_parts) > 1 else ""
                    
                    try:
                        # Parse versions
                        target_ver_parts = target_ver_str.split('.')
                        data_ver_parts = data_ver_str.split('.')
                        
                        target_major = int(target_ver_parts[0]) if target_ver_parts[0] else 0
                        data_major = int(data_ver_parts[0]) if data_ver_parts[0] else 0
                        
                        # Must have same major version
                        if target_major != data_major or target_major == 0:
                            continue
                        
                        # If both have minor versions, they must match EXACTLY
                        if len(target_ver_parts) > 1 and len(data_ver_parts) > 1:
                            target_minor = int(target_ver_parts[1])
                            data_minor = int(data_ver_parts[1])
                            # Exact match required: 3.7 matches 3.7, but NOT 3.5
                            if target_minor == data_minor:
                                return True
                        # If target has minor version (3.7) but data doesn't (3), allow it
                        # This allows "Claude 3 Sonnet" to match "Claude 3.7 Sonnet"
                        elif len(target_ver_parts) > 1 and len(data_ver_parts) == 1:
                            return True
                        # If both have no minor version, they match
                        elif len(target_ver_parts) == 1 and len(data_ver_parts) == 1:
                            return True
                        # If target has no minor but data has minor (e.g., "3" vs "3.5"), don't match
                        # This prevents "Claude 3.7 Sonnet" from matching "Claude 3.5 Sonnet"
                        else:
                            continue
                    except (ValueError, IndexError):
                        pass
                
                # 5. Llama models: Must match BOTH version AND size
                elif "llama" in target_clean.lower() and "instruct" in target_clean.lower():
                    # Extract version and size from target: "Llama 3.2 11B Instruct"
                    target_version = None
                    target_size = None
                    for part in target_parts:
                        if '.' in part and part.replace('.', '').replace('-', '').isdigit():
                            target_version = part
                        elif 'b' in part.lower() or 'm' in part.lower():
                            size_str = part.lower().replace('b', '').replace('m', '').replace('-', '')
                            if size_str.isdigit():
                                target_size = part.lower()
                    
                    # Extract version and size from data: "Llama 3 70B Instruct"
                    data_version = None
                    data_size = None
                    for part in data_parts:
                        if '.' in part and part.replace('.', '').replace('-', '').isdigit():
                            data_version = part
                        elif 'b' in part.lower() or 'm' in part.lower():
                            size_str = part.lower().replace('b', '').replace('m', '').replace('-', '')
                            if size_str.isdigit():
                                data_size = part.lower()
                    
                    # Both version and size must match exactly
                    if target_version and target_size and data_version and data_size:
                        # Check version match (major version must match)
                        version_match = False
                        try:
                            target_major = int(target_version.split('.')[0])
                            data_major = int(data_version.split('.')[0])
                            if target_major == data_major:
                                # If both have minor versions, they must match
                                if '.' in target_version and '.' in data_version:
                                    target_minor = int(target_version.split('.')[1])
                                    data_minor = int(data_version.split('.')[1])
                                    version_match = (target_minor == data_minor)
                                elif '.' in target_version:
                                    # Target has minor, data doesn't - check if minor matches expected
                                    version_match = True  # Allow "3" to match "3.2"
                                else:
                                    version_match = True
                        except (ValueError, IndexError):
                            pass
                        
                        # Check size match (must be exact)
                        size_match = (target_size.lower() == data_size.lower())
                        
                        # Both must match
                        if version_match and size_match:
                            return True
                
            return False
        
        # Filter raw data - ONLY show models that match configured models
        # Also normalize matched models to use configured model names (consolidate "Claude 3 Sonnet" -> "Claude 3.7 Sonnet")
        if "model_name" in raw_df.columns:
            if target_models:
                # First clean the model names in raw data
                raw_df_clean = raw_df.copy()
                raw_df_clean["model_name"] = raw_df_clean["model_name"].apply(clean_model_name)
                
                # Function to normalize model name to configured name if it matches
                def normalize_to_configured(data_model_name):
                    for target_model in target_models:
                        if matches_target_model(data_model_name, [target_model]):
                            return target_model  # Return the configured model name
                    return data_model_name  # Return original if no match
                
                # Filter to only include models that match target models
                mask = raw_df_clean["model_name"].apply(lambda x: matches_target_model(x, target_models))
                filtered_raw = raw_df_clean[mask].copy()
                
                # Normalize matched model names to configured names (consolidate duplicates)
                if not filtered_raw.empty:
                    filtered_raw["model_name"] = filtered_raw["model_name"].apply(normalize_to_configured)
                
                # Double-check: ensure all remaining rows match configured models
                if not filtered_raw.empty:
                    final_mask = filtered_raw["model_name"].apply(lambda x: matches_target_model(x, target_models))
                    filtered_raw = filtered_raw[final_mask].copy()
                
                # If no matches found, don't show fallback data - keep it empty
                # This ensures we only show configured models
            else:
                filtered_raw = raw_df.copy()
        else:
            filtered_raw = raw_df.copy()
        
        # Filter aggregated data - ONLY show models that match configured models
        # Also normalize matched models to use configured model names
        if "model_name" in agg_df.columns:
            if target_models:
                # First clean the model names in aggregated data (handle tuple format)
                agg_df_clean = agg_df.copy()
                if "model_name" in agg_df_clean.columns:
                    agg_df_clean["model_name"] = agg_df_clean["model_name"].apply(clean_model_name)
                
                # Function to normalize model name to configured name if it matches
                def normalize_to_configured(data_model_name):
                    for target_model in target_models:
                        if matches_target_model(data_model_name, [target_model]):
                            return target_model  # Return the configured model name
                    return data_model_name  # Return original if no match
                
                # Filter to only include models that match target models (strict matching)
                mask = agg_df_clean["model_name"].apply(lambda x: matches_target_model(x, target_models))
                filtered_agg = agg_df_clean[mask].copy()
                
                # Normalize matched model names to configured names (consolidate duplicates)
                if not filtered_agg.empty and "model_name" in filtered_agg.columns:
                    filtered_agg["model_name"] = filtered_agg["model_name"].apply(normalize_to_configured)
                    
                    # After normalization, deduplicate: if multiple rows have same normalized model name, aggregate them
                    # This handles cases where "Claude 3 Sonnet" and "Claude 3.7 Sonnet" both normalize to "Claude 3.7 Sonnet"
                    if len(filtered_agg) > len(filtered_agg["model_name"].unique()):
                        # Group by normalized model name and aggregate numeric columns
                        numeric_cols = ['count', 'success_count', 'error_count', 'avg_input_tokens', 
                                       'avg_output_tokens', 'p50_latency_ms', 'p95_latency_ms', 'p99_latency_ms',
                                       'min_latency_ms', 'max_latency_ms', 'json_valid_pct', 
                                       'avg_cost_usd_per_request', 'total_cost_usd']
                        
                        # Aggregate by model_name
                        agg_dict = {}
                        for col in filtered_agg.columns:
                            if col == 'model_name':
                                agg_dict[col] = 'first'  # Keep first model name
                            elif col in numeric_cols and col in filtered_agg.columns:
                                agg_dict[col] = 'sum' if 'total' in col or 'count' in col else 'mean'
                            else:
                                agg_dict[col] = 'first'
                        
                        filtered_agg = filtered_agg.groupby('model_name', as_index=False).agg(agg_dict)
                
                # Ensure we only keep rows that match exactly - no fallback
                # CRITICAL: Only keep models that are exactly in target_models list (after normalization)
                if not filtered_agg.empty:
                    # Final check: only keep models that are exactly in the configured target_models list
                    final_mask = filtered_agg["model_name"].apply(
                        lambda x: x in target_models  # Exact match - must be in target_models list
                    )
                    filtered_agg = filtered_agg[final_mask].copy()
                
                # If aggregated data is missing some models, try to create aggregates from raw data
                if not filtered_raw.empty and "model_name" in filtered_raw.columns:
                    # Check which target models are missing from aggregated data
                    missing_from_agg = []
                    for target_model in target_models:
                        has_match = False
                        if not filtered_agg.empty:
                            for agg_model_name in filtered_agg["model_name"]:
                                if matches_target_model(agg_model_name, [target_model]):
                                    has_match = True
                                    break
                        if not has_match:
                            # Check if raw data has this model
                            for raw_model_name in filtered_raw["model_name"]:
                                if matches_target_model(raw_model_name, [target_model]):
                                    missing_from_agg.append(target_model)
                                    break
                    
                    # If we have raw data for missing models, create simple aggregates
                    if missing_from_agg and not filtered_raw.empty:
                        # Create basic aggregation for missing models from raw data
                        for target_model in missing_from_agg:
                            model_raw_data = filtered_raw[
                                filtered_raw["model_name"].apply(lambda x: matches_target_model(x, [target_model]))
                            ]
                            if not model_raw_data.empty:
                                # Helper function to safely convert to numeric
                                def safe_numeric(series, default=0):
                                    if series is None or series.empty:
                                        return default
                                    try:
                                        numeric_series = pd.to_numeric(series, errors='coerce')
                                        return numeric_series.dropna()
                                    except:
                                        return pd.Series([default])
                                
                                # Safely convert numeric columns
                                latency_numeric = safe_numeric(model_raw_data.get("latency_ms", pd.Series()), 0)
                                input_tokens_numeric = safe_numeric(model_raw_data.get("input_tokens", pd.Series()), 0)
                                output_tokens_numeric = safe_numeric(model_raw_data.get("output_tokens", pd.Series()), 0)
                                json_valid_numeric = safe_numeric(model_raw_data.get("json_valid", pd.Series()), 0)
                                
                                # Get cost columns (try both possible column names)
                                cost_col = None
                                if "cost_usd_total" in model_raw_data.columns:
                                    cost_col = safe_numeric(model_raw_data["cost_usd_total"], 0)
                                elif "cost_usd" in model_raw_data.columns:
                                    cost_col = safe_numeric(model_raw_data["cost_usd"], 0)
                                else:
                                    cost_col = pd.Series([0])
                                
                                # Create a simple aggregate row
                                agg_row = {
                                    "model_name": target_model,
                                    "count": len(model_raw_data),
                                    "success_count": len(model_raw_data[model_raw_data.get("status", "") == "success"]) if "status" in model_raw_data.columns else len(model_raw_data),
                                    "error_count": len(model_raw_data[model_raw_data.get("status", "") == "error"]) if "status" in model_raw_data.columns else 0,
                                    "avg_input_tokens": float(input_tokens_numeric.mean()) if not input_tokens_numeric.empty else 0,
                                    "avg_output_tokens": float(output_tokens_numeric.mean()) if not output_tokens_numeric.empty else 0,
                                    "p50_latency_ms": float(latency_numeric.median()) if not latency_numeric.empty else 0,
                                    "p95_latency_ms": float(latency_numeric.quantile(0.95)) if not latency_numeric.empty else 0,
                                    "p99_latency_ms": float(latency_numeric.quantile(0.99)) if not latency_numeric.empty else 0,
                                    "min_latency_ms": float(latency_numeric.min()) if not latency_numeric.empty else 0,
                                    "max_latency_ms": float(latency_numeric.max()) if not latency_numeric.empty else 0,
                                    "json_valid_pct": float(json_valid_numeric.mean() * 100) if not json_valid_numeric.empty else 0,
                                    "avg_cost_usd_per_request": float(cost_col.mean()) if not cost_col.empty else 0,
                                    "total_cost_usd": float(cost_col.sum()) if not cost_col.empty else 0,
                                }
                                # Add to filtered_agg
                                filtered_agg = pd.concat([filtered_agg, pd.DataFrame([agg_row])], ignore_index=True)
                
                # Don't show all aggregated data as fallback - only show configured models
                # If filtered_agg is empty, keep it empty (don't show unconfigured models)
            else:
                filtered_agg = agg_df.copy()
        else:
            filtered_agg = agg_df.copy()
        
        # Premium Summary Cards
        st.header("📈 Executive Summary")
        
        # Check which configured models have data (in both aggregated and raw)
        models_with_data = set()
        if not filtered_agg.empty and "model_name" in filtered_agg.columns:
            for model_name in filtered_agg["model_name"]:
                cleaned = clean_model_name(model_name)
                models_with_data.add(cleaned)
        
        # Also check raw data for models that might not be aggregated yet
        models_in_raw = set()
        if not filtered_raw.empty and "model_name" in filtered_raw.columns:
            for model_name in filtered_raw["model_name"].unique():
                cleaned = clean_model_name(model_name)
                models_in_raw.add(cleaned)
        
        # Show helpful warning/info if some configured models don't have data
        if target_models:
            missing_models = []
            models_with_any_data = []
            for target_model in target_models:
                # Check if this target model has any matching data in aggregated or raw
                has_match = False
                # Check aggregated data
                for data_model in models_with_data:
                    if matches_target_model(data_model, [target_model]):
                        has_match = True
                        models_with_any_data.append(target_model)
                        break
                # If not found in aggregated, check raw data
                if not has_match:
                    for data_model in models_in_raw:
                        if matches_target_model(data_model, [target_model]):
                            has_match = True
                            models_with_any_data.append(target_model)
                            break
                if not has_match:
                    missing_models.append(target_model)
            
            # Show warning only if we have some data but not all
            if missing_models and (not filtered_agg.empty or not filtered_raw.empty):
                # Check what models we actually have data for
                available_models = []
                if not filtered_agg.empty and "model_name" in filtered_agg.columns:
                    available_models.extend(filtered_agg["model_name"].unique().tolist())
                if not filtered_raw.empty and "model_name" in filtered_raw.columns:
                    available_models.extend(filtered_raw["model_name"].unique().tolist())
                available_models = list(set(available_models))
                
                st.warning(f"""
                ⚠️ **No data found for configured model(s)**: {', '.join(missing_models)}
                
                **Configured models**: {', '.join(target_models)}  
                **Available data**: {', '.join([clean_model_name(m) for m in available_models[:3]])}{'...' if len(available_models) > 3 else ''}
                
                To see data for all configured models, run a new evaluation using the sidebar. 
                The dashboard will use the correct model IDs from your configuration.
                """)
            elif missing_models and filtered_agg.empty:
                st.info(f"""
                📊 **No evaluation data found for your configured models**: {', '.join(target_models)}
                
                To get started:
                1. Use the sidebar to enter a prompt or upload a file
                2. Select the models you want to test
                3. Click "🚀 Run Evaluation"
                
                Your configured models are: {', '.join(target_models)}
                """)
        
        if not filtered_agg.empty:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown("""
                <div class="metric-highlight">
                    <h3 style="margin: 0; font-size: 2rem; color: white; font-weight: 700;">{:,}</h3>
                    <p style="margin: 0.5rem 0 0 0; opacity: 0.9; color: white;">Total Evaluations</p>
                </div>
                """.format(len(filtered_raw) if not filtered_raw.empty else 0), unsafe_allow_html=True)
            
            with col2:
                success_rate = 0
                if not filtered_raw.empty and "status" in filtered_raw.columns:
                    total = len(filtered_raw)
                    success = len(filtered_raw[filtered_raw["status"] == "success"])
                    success_rate = (success / total * 100) if total > 0 else 0
                
                success_color = "#00b09b" if success_rate >= 90 else "#eea849"
                st.markdown(f"""
                <div class="premium-card" style="text-align: center; background: linear-gradient(135deg, {success_color} 0%, #96c93d 100%); color: white;">
                    <h3 style="margin: 0; font-size: 2rem;">{success_rate:.1f}%</h3>
                    <p style="margin: 0; opacity: 0.9;">Success Rate</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                total_cost = filtered_agg["total_cost_usd"].sum() if "total_cost_usd" in filtered_agg.columns else 0
                st.markdown(f"""
                <div class="premium-card" style="text-align: center;">
                    <h3 style="margin: 0; font-size: 2rem; color: #333; font-weight: 700;">${total_cost:.4f}</h3>
                    <p style="margin: 0.5rem 0 0 0; color: #666; font-weight: 500;">Total Cost</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                num_models = len(filtered_agg)
                st.markdown(f"""
                <div class="premium-card" style="text-align: center;">
                    <h3 style="margin: 0; font-size: 2rem; color: #333; font-weight: 700;">{num_models}</h3>
                    <p style="margin: 0.5rem 0 0 0; color: #666; font-weight: 500;">Models Compared</p>
                </div>
                """, unsafe_allow_html=True)

        # Enhanced Best Performers Section
        if not filtered_agg.empty and len(filtered_agg) > 0:
            st.header("🏆 Performance Leaders")
            
            leader_cols = st.columns(3)
            metrics_to_show = [
                ("⚡ Fastest Response", "p95_latency_ms", "min", "#00b09b"),
                ("💰 Most Cost-Effective", "avg_cost_usd_per_request", "min", "#667eea"),
                ("✅ Best Quality", "json_valid_pct", "max", "#96c93d")
            ]
            
            for idx, (title, metric, operation, color) in enumerate(metrics_to_show):
                with leader_cols[idx]:
                    if metric in filtered_agg.columns:
                        if operation == "min":
                            best_idx = filtered_agg[metric].idxmin()
                        else:
                            best_idx = filtered_agg[metric].idxmax()
                        
                        best_model = filtered_agg.loc[best_idx, "model_name"]
                        best_value = filtered_agg.loc[best_idx, metric]
                        
                        unit = " ms" if "latency" in metric else "%" if "pct" in metric else ""
                        st.markdown(f"""
                        <div class="premium-card" style="border-left: 4px solid {color}; text-align: center;">
                            <h4 style="margin: 0 0 1rem 0; color: {color};">{title}</h4>
                            <h3 style="margin: 0; color: #333;">{best_model}</h3>
                            <p style="margin: 0.5rem 0 0 0; color: #666; font-size: 1.1rem;">
                                {best_value:.2f}{unit}
                            </p>
                        </div>
                        """, unsafe_allow_html=True)

        # Enhanced Interactive Visualizations
        # Ensure we use the most up-to-date synced data
        if not filtered_raw.empty and len(filtered_raw) > 0:
            st.header("📊 Interactive Analytics")
            
            # Custom visualization selector
            viz_option = st.selectbox(
                "Choose Visualization Type",
                ["Performance Dashboard", "Cost Analysis", "Quality Metrics", "Token Usage"],
                help="Select which metrics to visualize"
            )
            
            # Use synced data - ensure fresh copy from loaded data
            success_df = filtered_raw[filtered_raw["status"] == "success"].copy() if "status" in filtered_raw.columns else filtered_raw.copy()
            
            # CRITICAL: Final verification - ensure only configured models are shown
            if not success_df.empty and target_models and "model_name" in success_df.columns:
                final_verification = success_df["model_name"].apply(
                    lambda x: matches_target_model(x, target_models)
                )
                success_df = success_df[final_verification].copy()
            
            if not success_df.empty:
                if viz_option == "Performance Dashboard":
                    col1, col2 = st.columns(2)
                    with col1:
                        if "latency_ms" in success_df.columns and "model_name" in success_df.columns:
                            fig = px.box(success_df, x="model_name", y="latency_ms", 
                                        title="🚀 Response Time Distribution",
                                        color="model_name",
                                        color_discrete_sequence=px.colors.qualitative.Set2)
                            fig.update_layout(showlegend=False, height=400, template="plotly_white")
                            st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        if "model_name" in success_df.columns:
                            requests_per_model = success_df['model_name'].value_counts().reset_index()
                            requests_per_model.columns = ['model_name', 'request_count']
                            fig = px.bar(requests_per_model, x='model_name', y='request_count',
                                        title="📊 Requests per Model",
                                        color='model_name',
                                        color_discrete_sequence=px.colors.qualitative.Pastel)
                            fig.update_layout(showlegend=False, height=400, template="plotly_white")
                            st.plotly_chart(fig, use_container_width=True)
                
                elif viz_option == "Cost Analysis":
                    if "cost_usd_total" in success_df.columns:
                        col1, col2 = st.columns(2)
                        with col1:
                            fig = px.box(success_df, x="model_name", y="cost_usd_total",
                                        title="💰 Cost Distribution",
                                        color="model_name",
                                        color_discrete_sequence=px.colors.qualitative.Set3)
                            fig.update_layout(showlegend=False, height=400, template="plotly_white")
                            st.plotly_chart(fig, use_container_width=True)
                        
                        with col2:
                            if not filtered_agg.empty and "avg_cost_usd_per_request" in filtered_agg.columns:
                                fig = px.bar(filtered_agg.sort_values("avg_cost_usd_per_request"),
                                            x="model_name", y="avg_cost_usd_per_request",
                                            title="💰 Average Cost per Request",
                                            color="avg_cost_usd_per_request",
                                            color_continuous_scale="Greens")
                                fig.update_layout(height=400, template="plotly_white")
                                st.plotly_chart(fig, use_container_width=True)
                
                elif viz_option == "Quality Metrics":
                    if "json_valid" in success_df.columns:
                        json_stats = success_df.groupby("model_name")["json_valid"].agg(["sum", "count"])
                        json_stats["validity_pct"] = (json_stats["sum"] / json_stats["count"] * 100).round(2)
                        json_stats = json_stats.reset_index()
                        
                        fig = px.bar(json_stats.sort_values("validity_pct", ascending=False),
                                    x="model_name", y="validity_pct",
                                    title="✅ JSON Validity Percentage",
                                    color="validity_pct",
                                    color_continuous_scale="RdYlGn",
                                    text="validity_pct")
                        fig.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                        fig.update_layout(height=400, template="plotly_white")
                        st.plotly_chart(fig, use_container_width=True)
                
                elif viz_option == "Token Usage":
                    col1, col2 = st.columns(2)
                    with col1:
                        if "input_tokens" in success_df.columns:
                            token_input = success_df.groupby("model_name")["input_tokens"].mean().reset_index()
                            fig = px.bar(token_input, x="model_name", y="input_tokens",
                                        title="📥 Average Input Tokens",
                                        color="model_name",
                                        color_discrete_sequence=px.colors.qualitative.Pastel)
                            fig.update_layout(showlegend=False, height=400, template="plotly_white")
                            st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        if "output_tokens" in success_df.columns:
                            token_output = success_df.groupby("model_name")["output_tokens"].mean().reset_index()
                            fig = px.bar(token_output, x="model_name", y="output_tokens",
                                        title="📤 Average Output Tokens",
                                        color="model_name",
                                        color_discrete_sequence=px.colors.qualitative.Pastel)
                            fig.update_layout(showlegend=False, height=400, template="plotly_white")
                            st.plotly_chart(fig, use_container_width=True)
    else:
        # Empty state with call to action
        st.markdown("""
        <div class="premium-card" style="text-align: center; padding: 4rem;">
            <h2 style="color: #667eea;">📊 No Data Yet</h2>
            <p style="color: #666; font-size: 1.1rem; margin-bottom: 2rem;">
                Start by testing your first prompt to see beautiful analytics!
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("🚀 Test Your First Prompt", type="primary", use_container_width=True):
            st.info("💡 Use the sidebar to run evaluations!")

# ==========================================
# TAB 2: Premium Historical Results
# ==========================================
with tab2:
    st.header("📈 Historical Analysis & Export")
    
    # Reload data with current cache key to ensure sync in Tab 2
    raw_df, agg_df = load_data(raw_path, agg_path, st.session_state.data_reload_key)
    
    if raw_df.empty:
        st.info("""
        📭 **No Historical Data Available**
        
        Use the sidebar to run evaluations and build your historical dataset.
        """)
    else:
        overview_col1, overview_col2, overview_col3, overview_col4 = st.columns(4)
        
        with overview_col1:
            st.metric("Total Records", f"{len(raw_df):,}")
        
        with overview_col2:
            unique_models = raw_df['model_name'].nunique() if 'model_name' in raw_df.columns else 0
            st.metric("Unique Models", unique_models)
        
        with overview_col3:
            date_range = "N/A"
            if 'timestamp' in raw_df.columns:
                try:
                    dates = pd.to_datetime(raw_df['timestamp'])
                    date_range = f"{dates.min().strftime('%Y-%m-%d')} to {dates.max().strftime('%Y-%m-%d')}"
                except:
                    pass
            st.metric("Date Range", date_range)
        
        with overview_col4:
            if 'status' in raw_df.columns:
                success_rate = (raw_df['status'] == 'success').mean() * 100
            else:
                success_rate = 0
            st.metric("Success Rate", f"{success_rate:.1f}%")
        
        # Interactive data explorer
        st.subheader("🔍 Data Explorer")
        
        explore_col1, explore_col2 = st.columns([1, 3])
        
        with explore_col1:
            show_columns = st.multiselect(
                "Select columns to display",
                options=raw_df.columns.tolist(),
                default=['model_name', 'latency_ms', 'input_tokens', 'output_tokens', 'cost_usd_total', 'status'] if all(col in raw_df.columns for col in ['model_name', 'latency_ms', 'input_tokens', 'output_tokens', 'cost_usd_total', 'status']) else raw_df.columns.tolist()[:6]
            )
            
            rows_to_show = st.slider("Rows to display", 10, min(1000, len(raw_df)), 100)
        
        with explore_col2:
            display_columns = [col for col in show_columns if col in raw_df.columns]
            if display_columns:
                st.dataframe(
                    raw_df[display_columns].head(rows_to_show),
                    use_container_width=True,
                    height=400
                )
        
        # Enhanced export options
        st.subheader("💾 Advanced Export")
        
        export_col1, export_col2, export_col3 = st.columns(3)
        
        with export_col1:
            if not agg_df.empty:
                csv_agg = agg_df.to_csv(index=False)
                st.download_button(
                    label="📊 Aggregated Data",
                    data=csv_agg,
                    file_name=f"aggregated_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with export_col2:
            if not raw_df.empty:
                csv_raw = raw_df.to_csv(index=False)
                st.download_button(
                    label="📈 Raw Metrics",
                    data=csv_raw,
                    file_name=f"raw_metrics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        with export_col3:
            # Export configuration
            if Path(config_path).exists():
                try:
                    config_data = open(config_path, 'r', encoding='utf-8').read()
                    st.download_button(
                        label="⚙️ Configuration",
                        data=config_data,
                        file_name="model_configuration.yaml",
                        mime="text/yaml",
                        use_container_width=True
                    )
                except:
                    st.button("⚙️ Configuration", disabled=True, use_container_width=True)
            else:
                st.button("⚙️ Configuration", disabled=True, use_container_width=True)

# Premium Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 2rem;">
    <p style="font-size: 1.1rem; font-weight: 600; color: #667eea;">🚀 AI Cost Optimizer Pro</p>
    <p style="font-size: 0.9rem;">Enterprise-Grade LLM Performance & Cost Analytics</p>
    <p style="font-size: 0.85rem; margin-top: 0.5rem;">Built with Streamlit | Powered by AWS Bedrock</p>
</div>
""", unsafe_allow_html=True)
