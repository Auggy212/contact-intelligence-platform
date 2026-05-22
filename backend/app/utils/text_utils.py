import re


def truncate(text: str, max_chars: int = 500) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "…"


def strip_json_fences(text: str) -> str:
    """
    Strips markdown code fences from Claude responses.
    Handles ```json ... ``` and ``` ... ``` wrappers.
    """
    text = text.strip()
    match = re.match(r"^```(?:json)?\s*\n?(.*?)\n?```$", text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def count_tokens_approx(text: str) -> int:
    """Rough token count: ~4 chars per token for English."""
    return max(1, len(text) // 4)
