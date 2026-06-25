"""Pydantic models for common LLM JSON shapes (single text field or one object/dict)."""

from pydantic import BaseModel, ConfigDict


class LlmTextOutput(BaseModel):
    """Standard shape: ``{'text': '...'}`` (or ``null`` for optional bodies)."""

    model_config = ConfigDict(extra="ignore")

    text: str | None = None
