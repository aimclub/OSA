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

    # Peak memory of the detection stage is driven by these two. Pages are
    # rasterized at render_dpi and predicted layout_batch_size at a time, so on a
    # memory-tight machine lowering the DPI (quadratic) is the bigger lever and
    # shrinking the batch the safer one. Kept as literals rather than imported
    # from doc_pages so this module stays free of the optional layout stack.
    render_dpi: PositiveInt = 200
    layout_batch_size: PositiveInt = 4

    # Retries per element. Every VLM call used to be one-shot, so a single
    # transient error cost that element its text for good.
    vlm_max_retries: int = Field(default=15, ge=0)
    vlm_retry_delay: float = Field(default=2.0, ge=0.0)
    vlm_timeout: float = Field(default=120.0, gt=0.0)


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

    # How much of the document actually got described. A run where most requests
    # failed still produces a graph, just an empty-looking one, so the ratio has
    # to be reported rather than inferred from the artifacts.
    requested: int = 0
    described: int = 0
