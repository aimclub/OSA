from functools import lru_cache

import tiktoken


@lru_cache(maxsize=4)
def _get_encoder(encoding_name: str) -> tiktoken.Encoding:
    """Get a cached tiktoken encoder by name."""
    try:
        return tiktoken.get_encoding(encoding_name)
    except ValueError:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, encoding_name: str = "cl100k_base") -> int:
    """Count the number of tokens in text using the specified encoding."""
    if not text:
        return 0
    return len(_get_encoder(encoding_name).encode(text))


def truncate_to_tokens(
    text: str,
    max_tokens: int,
    encoding_name: str = "cl100k_base",
    mode: str = "start",
) -> str:
    """Truncate text to fit within max_tokens.

    Args:
        text: The text to truncate.
        max_tokens: Maximum number of tokens allowed.
        encoding_name: Tiktoken encoding name.
        mode: Truncation strategy — "start" keeps the beginning,
              "end" keeps the end, "middle-out" keeps both ends.

    Returns:
        The (possibly truncated) text.
    """
    if not text or max_tokens <= 0:
        return ""
    encoder = _get_encoder(encoding_name)
    tokens = encoder.encode(text)
    if len(tokens) <= max_tokens:
        return text
    if mode == "end":
        return encoder.decode(tokens[-max_tokens:])
    if mode == "middle-out":
        half = max_tokens // 2
        return encoder.decode(tokens[:half] + tokens[-half:])
    # default: "start"
    return encoder.decode(tokens[:max_tokens])
