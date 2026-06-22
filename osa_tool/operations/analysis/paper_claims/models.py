from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, PositiveInt


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PdfChunk(StrictModel):
    path: Path
    index: int
    start_page: int = Field(ge=1)
    end_page: int = Field(ge=1)
    source_path: Path
    source_hash: str


class MarkerOptions(StrictModel):
    extract_images: bool = False
    cache_root: Path | None = None
    force_refresh: bool = False
    marker_config: dict[str, Any] = Field(default_factory=dict)


class ConvertedChunk(StrictModel):
    index: int
    start_page: int
    end_page: int
    markdown: str
    cache_path: Path | None = None


class ConvertedDocument(StrictModel):
    source_path: Path
    source_hash: str
    chunks: list[ConvertedChunk]
    markdown: str
    cache_hit: bool = False
    cache_dir: Path | None = None


class HeadingMeta(StrictModel):
    raw: str
    level: int = Field(ge=1, le=6)
    numbering: str | None = None


class PaperSection(StrictModel):
    section_id: str
    name: str
    text: str
    heading_meta: HeadingMeta


class ClaimCategory(str, Enum):
    DATASET = "dataset"
    MODEL_ARCHITECTURE = "model_architecture"
    TRAINING_PROCEDURE = "training_procedure"
    EVALUATION_METRIC = "evaluation_metric"
    NUMERICAL_RESULT = "numerical_result"
    BASELINE_COMPARISON = "baseline_comparison"
    DATA_PREPROCESSING = "data_preprocessing"
    INFRASTRUCTURE = "infrastructure"


class Verifiability(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExtractedClaim(StrictModel):
    claim_id: str
    claim: str
    original_text: str
    category: ClaimCategory
    value: str | None = None
    verifiability: Verifiability
    section_id: str
    section_name: str
    section_heading_raw: str | None = None
    contradiction: bool = False


class DedupSelection(StrictModel):
    claim_id: str
    claim: str
    contradiction: bool


class ExtractionMetadata(StrictModel):
    source: str | None = None
    model: str | None = None
    steps: int = 3
    filtered_claims: int = 0
    step3_input_count: int = 0
    step3_output_count: int = 0


class ClaimExtractionResult(StrictModel):
    claims: list[ExtractedClaim]
    deduplication: list[DedupSelection]
    selected_section_ids: list[str]
    meta: ExtractionMetadata

    def to_legacy_dict(self) -> dict[str, Any]:
        claims = []
        for claim in self.claims:
            item = claim.model_dump(mode="json", exclude={"section_id"})
            claims.append(item)
        return {
            "result": claims,
            "step3_selection": [item.model_dump(mode="json") for item in self.deduplication],
            "meta": self.meta.model_dump(mode="json"),
        }


class PipelineOptions(StrictModel):
    pages_per_chunk: PositiveInt = 10
    marker: MarkerOptions = Field(default_factory=MarkerOptions)
    max_retries: PositiveInt = 5


class PipelineResult(StrictModel):
    converted_document: ConvertedDocument
    sections: list[PaperSection]
    extraction: ClaimExtractionResult

    def to_legacy_dict(self) -> dict[str, Any]:
        return self.extraction.to_legacy_dict()
