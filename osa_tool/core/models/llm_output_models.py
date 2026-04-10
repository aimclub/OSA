"""Pydantic models for common LLM JSON shapes (single text field or one object/dict)."""

from typing import Any

from pydantic import BaseModel, ConfigDict, RootModel


class LlmTextOutput(BaseModel):
    """Standard shape: ``{\"text\": \"...\"}`` (or ``null`` for optional bodies)."""

    model_config = ConfigDict(extra="ignore")

    text: str | None = None


class LlmJsonObject(RootModel[dict[str, Any]]):
    """LLM returns one JSON object; use ``.root`` as the ``dict``."""

    pass
