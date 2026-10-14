from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from osa_tool.operations.analysis.artifacts import ModelProvenance, StageReportMetadata, write_stage_report
from osa_tool.operations.analysis.paper_claims.models import (
    ClaimExtractionResult,
    LoadedClaimsArtifact,
    LoadedSectionsArtifact,
    PaperSection,
)
from osa_tool.utils.logger import logger


def load_claims_json(path: Path) -> LoadedClaimsArtifact:
    """Accept typed ``claims.json``, legacy ``claims_legacy.json``, or a bare list."""
    source_path = Path(path)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        claims, source_format, upstream_meta = payload, "bare", {}
    elif isinstance(payload, dict):
        if "claims" in payload:
            claims, source_format = payload["claims"], "typed"
        else:
            claims, source_format = payload.get("result"), "legacy"
        upstream_meta = payload.get("meta", {})
        if not isinstance(upstream_meta, dict):
            upstream_meta = {}
    else:
        claims, source_format, upstream_meta = None, "bare", {}
    if not isinstance(claims, list) or any(not isinstance(item, dict) for item in claims):
        raise ValueError("Claims JSON must contain a list under 'claims' or 'result', or be a list itself")
    return LoadedClaimsArtifact(
        claims=claims,
        source_path=source_path,
        source_format=source_format,
        upstream_meta=upstream_meta,
    )


def model_provenance_for_loaded(loaded: LoadedClaimsArtifact) -> ModelProvenance:
    """Keep model provenance from an imported typed claim artifact when present."""
    configured = loaded.upstream_meta.get("configured_model")
    if not isinstance(configured, str):
        configured = None
    upstream_model = loaded.upstream_meta.get("model")
    upstream_models = loaded.upstream_meta.get("models_used")
    used = (
        [model for model in upstream_models if isinstance(model, str) and model]
        if isinstance(upstream_models, list)
        else ([upstream_model] if isinstance(upstream_model, str) and upstream_model else [])
    )
    return ModelProvenance(configured=configured, used=list(dict.fromkeys(used)))


def export_loaded_claims(loaded: LoadedClaimsArtifact, output_dir: Path) -> Path:
    """Materialize imported claims as a resumable artifact and canonical stage report."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    provenance = model_provenance_for_loaded(loaded)
    upstream_model = loaded.upstream_meta.get("model")
    payload: dict[str, Any] = {
        "claims": loaded.claims,
        "meta": {
            "source": str(loaded.source_path),
            "model": upstream_model if isinstance(upstream_model, str) else None,
            "configured_model": provenance.configured,
            "models_used": provenance.used,
            "imported": True,
            "input_format": loaded.source_format,
            "upstream_meta": loaded.upstream_meta,
        },
    }
    claims_path = destination / "claims.json"
    claims_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_stage_report(
        destination,
        meta=StageReportMetadata(
            source={
                "paper": {"kind": "claims_json", "path": str(loaded.source_path)},
                "upstream": loaded.upstream_meta,
            },
            model=provenance,
        ),
        result=payload,
    )
    logger.info("Imported paper claims export completed: %s", claims_path)
    return claims_path


def load_sections_json(path: Path) -> LoadedSectionsArtifact:
    """Load generic parsed ``PaperSection`` JSON from a bare list or ``{"sections": [...]}`` envelope."""
    source_path = Path(path)
    payload = json.loads(source_path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        raw_sections, source_format, upstream_meta = payload, "bare", {}
    elif isinstance(payload, dict) and isinstance(payload.get("sections"), list):
        raw_sections, source_format = payload["sections"], "envelope"
        upstream_meta = payload.get("meta", {})
        if not isinstance(upstream_meta, dict):
            upstream_meta = {}
    else:
        raise ValueError('Sections JSON must be a list of PaperSection objects or an object with "sections": [...]')
    try:
        sections = [PaperSection.model_validate(item) for item in raw_sections]
    except ValidationError as exc:
        raise ValueError(
            "Sections JSON must use the PaperSection schema: "
            "section_id, name, text, heading_meta.raw, heading_meta.level"
        ) from exc
    if not sections:
        raise ValueError("Sections JSON must contain at least one PaperSection object")
    return LoadedSectionsArtifact(
        sections=sections,
        source_path=source_path,
        source_format=source_format,
        upstream_meta=upstream_meta,
    )


def write_sections_json(sections: list[PaperSection], output_dir: Path) -> Path:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    sections_path = destination / "sections.json"
    sections_path.write_text(
        json.dumps([item.model_dump(mode="json") for item in sections], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return sections_path


def export_section_extraction(
    extraction: ClaimExtractionResult,
    sections: list[PaperSection],
    output_dir: Path,
    *,
    source_kind: str,
    source_path: Path,
    model: ModelProvenance,
    upstream_meta: dict[str, Any] | None = None,
) -> Path:
    """Export parsed-section extraction with the same stage artifacts as PDF extraction."""
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    write_sections_json(sections, destination)
    payload = extraction.model_dump(mode="json")
    claims_path = destination / "claims.json"
    claims_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    source: dict[str, Any] = {"paper": {"kind": source_kind, "path": str(source_path)}}
    if upstream_meta:
        source["upstream"] = upstream_meta
    write_stage_report(
        destination,
        meta=StageReportMetadata(source=source, model=model),
        result=payload,
    )
    logger.info("Parsed-section paper claims export completed: %s", claims_path)
    return claims_path
