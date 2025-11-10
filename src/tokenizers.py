"""Token counting wrapper with best-available implementations and fallbacks."""

from typing import Optional
import re

try:
    import tiktoken  # type: ignore
except ImportError:
    tiktoken = None  # type: ignore

try:
    # Try to import sentencepiece for Llama (if available)
    import sentencepiece as spm  # type: ignore
    HAS_SENTENCEPIECE = True
except ImportError:
    HAS_SENTENCEPIECE = False
    spm = None  # type: ignore


def count_tokens(model_tokenizer: str, text: str) -> int:
    """
    Count tokens for text using the appropriate tokenizer.
    
    Args:
        model_tokenizer: Tokenizer type ('anthropic', 'llama', 'heuristic', etc.)
        text: Text to tokenize
    
    Returns:
        Estimated token count
    """
    tokenizer_type = model_tokenizer.lower().strip()
    
    # Anthropic models (Claude) - use GPT-4 tokenizer as approximation
    if tokenizer_type == "anthropic":
        return _count_with_tiktoken(text, "cl100k_base") or _heuristic_count_anthropic(text)
    
    # Llama models
    if tokenizer_type == "llama":
        # Llama typically uses SentencePiece, but we'll use GPT-2 as approximation
        return _count_with_tiktoken(text, "gpt2") or _heuristic_count_llama(text)
    
    # Amazon models (Titan, Nova) - use heuristic
    if tokenizer_type in ("heuristic", "titan", "amazon", "nova"):
        return _heuristic_count(text)
    
    # Qwen models - use GPT-2 tokenizer as approximation
    if tokenizer_type == "qwen":
        return _count_with_tiktoken(text, "gpt2") or _heuristic_count_llama(text)
    
    # Alibaba models - similar to Qwen
    if tokenizer_type == "alibaba":
        return _count_with_tiktoken(text, "gpt2") or _heuristic_count_llama(text)
    
    # Fallback to heuristic
    return _heuristic_count(text)


def _count_with_tiktoken(text: str, encoding_name: str) -> Optional[int]:
    """Count tokens using tiktoken if available."""
    if tiktoken is None:
        return None
    
    try:
        encoding = tiktoken.get_encoding(encoding_name)
        return len(encoding.encode(text))
    except Exception:
        return None


def _heuristic_count_anthropic(text: str) -> int:
    """Heuristic count for Anthropic models (Claude)."""
    # Anthropic uses a character-based approach with ~4 chars per token
    # More accurate: count words and punctuation separately
    words = len(text.split())
    chars = len(text)
    # Average: ~4 chars per token, or ~0.75 tokens per word
    return int((chars / 4) + (words * 0.25))


def _heuristic_count_llama(text: str) -> int:
    """Heuristic count for Llama models."""
    # Llama tokenizer is similar to GPT-2, ~0.75 tokens per word
    words = len(text.split())
    chars = len(text)
    # Llama typically has ~3.5 chars per token
    return int((chars / 3.5) + (words * 0.3))


def _heuristic_count(text: str) -> int:
    """
    General heuristic token counting.
    
    Estimates tokens based on word count and character count.
    Average is ~4 characters per token for most tokenizers.
    """
    if not text:
        return 0
    
    words = len(text.split())
    chars = len(text)
    
    # Weighted average: 70% chars/4, 30% words*1.3
    token_estimate = int((chars / 4) * 0.7 + (words * 1.3) * 0.3)
    return max(1, token_estimate)


