from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PaperParsingOptions(StrictModel):
    """Tunables for :class:`~...pipeline.PaperParsingPipeline`.

    The VLM connection (model, base URL, API key, system prompt) is configured
    on the pipeline itself; these options control the layout-detection and
    description stages.
    """

    device: str = "cpu"
    conf_threshold: float = Field(default=0.15, gt=0.0, le=1.0)
    max_concurrent: PositiveInt = 5
    downsample_factor: PositiveInt = 6
    save_img: bool = False


class PaperParsingResult(StrictModel):
    """Output of the paper-parsing pipeline.

    ``report`` is the list of layout elements (each carrying VLM ``text`` /
    ``description``) and ``graph`` is the document graph built from it; both are
    kept as plain containers because they hold non-JSON payloads such as encoded
    image crops. ``markdown`` is the reading-order linearization consumed by
    downstream prompts.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    source_path: Path
    markdown: str
    report: list[dict[str, Any]] = Field(default_factory=list)
    graph: dict[str, Any] = Field(default_factory=dict)
