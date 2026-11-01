"""Stable JSON artifact envelopes shared by analysis operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class _StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ModelProvenance(_StrictModel):
    """Configured model and the distinct successful models used by one stage."""

    configured: str | None = None
    used: list[str] = Field(default_factory=list)


class StageReportMetadata(_StrictModel):
    """Input and model provenance stored with every canonical stage report."""

    source: dict[str, Any] = Field(default_factory=dict)
    model: ModelProvenance = Field(default_factory=ModelProvenance)


class StageReport(_StrictModel):
    """Versioned, module-owned JSON report envelope."""

    schema_version: str = "1.0"
    meta: StageReportMetadata
    result: Any


def model_provenance(handler: Any | None, *, configured: str | None = None) -> ModelProvenance:
    """Build provenance without requiring non-production test handlers to implement it."""
    if configured is None and handler is not None:
        configured = getattr(getattr(handler, "model_settings", None), "model", None)
    if not isinstance(configured, str):
        configured = None

    recorded = getattr(handler, "successful_models", None) if handler is not None else None
    used = [model for model in recorded if isinstance(model, str) and model] if isinstance(recorded, list) else []
    if not used and handler is not None:
        last_successful = getattr(handler, "last_successful_model", None)
        if isinstance(last_successful, str) and last_successful:
            used = [last_successful]
    return ModelProvenance(configured=configured, used=list(dict.fromkeys(used)))


def write_stage_report(output_dir: Path, *, meta: StageReportMetadata, result: Any) -> Path:
    """Persist one canonical stage report and return its path."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    report_path = destination / "report.json"
    payload = StageReport(meta=meta, result=result).model_dump(mode="json")
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return report_path
