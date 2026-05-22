from typing import Any

import anthropic

from app.core.config import settings
from app.core.exceptions import AIError
from app.core.logging import get_logger

logger = get_logger(__name__)

_client: anthropic.AsyncAnthropic | None = None


def get_anthropic_client() -> anthropic.AsyncAnthropic:
    global _client
    if _client is None:
        _client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    return _client


async def call_claude(
    messages: list[dict[str, Any]],
    system: str,
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.0,
) -> tuple[str, dict[str, int]]:
    """
    Calls Claude and returns (response_text, token_usage_dict).
    temperature=0 for deterministic agent outputs.
    """
    client = get_anthropic_client()
    used_model = model or settings.ANTHROPIC_MODEL

    try:
        response = await client.messages.create(
            model=used_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=messages,
        )
        text = response.content[0].text
        usage = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }
        logger.debug(
            "claude_call_complete",
            model=used_model,
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
        )
        return text, usage
    except anthropic.APIError as exc:
        logger.error("claude_api_error", error=str(exc), model=used_model)
        raise AIError(f"Claude API error: {exc}") from exc
