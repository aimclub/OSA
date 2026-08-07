from osa_tool.config.settings import ModelSettings

BASE_SETTINGS = {
    "rate_limit": 10,
    "base_url": "https://openrouter.ai/api/v1",
    "encoder": "cl100k_base",
    "host_name": "https://openrouter.ai/api/v1",
    "localhost": "http://localhost:11434/",
    "model": "text-only-model",
    "fallback_models": [],
    "path": "chat/completions",
    "temperature": 0.05,
    "max_tokens": 1000,
    "context_window": 1000,
    "top_p": 0.95,
    "max_retries": 3,
    "allowed_providers": [],
    "system_prompt": "You are a technical document specialist.",
}


def make_settings(**extras) -> ModelSettings:
    """Validation model settings carrying the ``vlm_*`` / ``paper_parser_*`` extras."""
    return ModelSettings(**BASE_SETTINGS, **extras)
