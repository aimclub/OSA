from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

PdfParserName = Literal["marker", "mistral-ocr", "cloudflare-ai"]


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
    low_vram: bool = True
    process_isolation: bool = True
    log_cuda_memory: bool = True
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
    parser: PdfParserName | None = None


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
    SOURCE_ASSERTION = "source_assertion"
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


class ClaimSource(StrictModel):
    claim_id: str
    claim: str
    original_text: str
    section_id: str
    section_name: str
    section_heading_raw: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


FindingKind = Literal["direct_conflict", "reporting_gap", "comparison_scope", "unclear_description", "none"]
FindingSupport = Literal["fully_supported", "partially_supported", "not_supported", "insufficient_evidence"]
FindingTarget = Literal["left", "right", "both", "undetermined"]


class ClaimReviewComment(StrictModel):
    """A mark on one claim: which other claim it concerns, what kind of issue, and why.

    The full review of the pair (both sides, quotes, evidence) stays in PairReview under the same pair_id.
    """

    pair_id: str
    category: Literal["contradiction", "potential_inconsistency", "reporting_issue"]
    role: Literal["participant", "affected_claim", "supporting_context", "review_context"]
    other_claim_id: str | None = None
    other_source_claim_id: str | None = None
    finding_kind: FindingKind | None = None
    comment: str = ""


class ReviewSide(StrictModel):
    source_claim_id: str
    claim_id: str | None
    claim: str
    quote: str = ""


class PairReview(StrictModel):
    pair_id: str
    left: ReviewSide
    right: ReviewSide
    consistency_status: str
    finding_kind: FindingKind | None = None
    finding_support: FindingSupport | None = None
    finding_target: FindingTarget = "undetermined"
    reason: str
    evidence_ids: list[str]


def summarize_pair_reviews(claims: list[dict[str, Any]], analysis: dict[str, Any]) -> list[PairReview]:
    representatives = {c["claim_id"]: c["claim_id"] for c in claims if "claim_id" in c}
    for c in claims:
        for source in c.get("sources", []):
            if isinstance(source, dict) and source.get("claim_id") and c.get("claim_id"):
                representatives[source["claim_id"]] = c["claim_id"]
    pairs = {p["pair_id"]: p for p in analysis.get("candidate_pairs", [])}

    def side(item, quote):
        source_id = item["claim_id"]
        return ReviewSide(source_claim_id=source_id, claim_id=representatives.get(source_id),
                          claim=item["claim"], quote=quote)

    return [PairReview(pair_id=d["pair_id"], left=side(pairs[d["pair_id"]]["left"], d.get("left_claim_quote", "")),
                       right=side(pairs[d["pair_id"]]["right"], d.get("right_claim_quote", "")), consistency_status=d["status"],
                       finding_target=d.get("finding_target", "undetermined"),
                       finding_kind=d.get("finding_kind"), finding_support=d.get("finding_support"),
                       reason=d["reason"], evidence_ids=d["evidence_ids"])
            for d in analysis.get("decisions", [])]


def review_annotations(claims, analysis):
    """Map validated reviews to surviving representatives, retaining their original quote in PairReview."""
    comments = {c["claim_id"]: [] for c in claims if "claim_id" in c}
    warnings = {cid: [] for cid in comments}
    for review in summarize_pair_reviews(claims, analysis):
        status = review.consistency_status
        is_pair = status in ("contradiction", "potential_inconsistency")
        if not is_pair and review.finding_support not in ("fully_supported", "partially_supported"):
            continue
        left, right = review.left.claim_id, review.right.claim_id
        if is_pair and (not left or not right or left == right):
            continue
        for side, own, other in (("left", review.left, review.right), ("right", review.right, review.left)):
            cid = own.claim_id
            if cid is None or (side == "right" and left == right):
                continue
            # Both sides can collapse into one surviving claim; it then has no distinct counterpart.
            other_id = other.claim_id if other.claim_id != cid else None
            if is_pair:
                role = "participant"
            elif review.finding_target == "undetermined":
                role = "review_context"
            elif left == right or review.finding_target in ("both", side):
                role = "affected_claim"
            else:
                role = "supporting_context"
            comments[cid].append(ClaimReviewComment(
                pair_id=review.pair_id, category=status if is_pair else "reporting_issue", role=role,
                other_claim_id=other_id, other_source_claim_id=other.source_claim_id,
                finding_kind=review.finding_kind, comment=review.reason))
            if status == "potential_inconsistency" and other_id and other_id not in warnings[cid]:
                warnings[cid].append(other_id)
    return {cid: {"review_comments": items, "potential_inconsistency_claim_ids": warnings[cid]}
            for cid, items in comments.items()}


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
    contradicts_claim_ids: list[str] = Field(default_factory=list)
    potential_inconsistency_claim_ids: list[str] = Field(default_factory=list)
    review_comments: list[ClaimReviewComment] = Field(default_factory=list)
    sources: list[ClaimSource] = Field(default_factory=list)


class DedupSelection(StrictModel):
    claim_id: str
    claim: str
    contradiction: bool


class ExtractionMetadata(StrictModel):
    source: str | None = None
    model: str | None = None
    configured_model: str | None = None
    models_used: list[str] = Field(default_factory=list)
    steps: int = 3
    filtered_claims: int = 0
    step3_input_count: int = 0
    step3_output_count: int = 0


class ClaimExtractionResult(StrictModel):
    deduplication_audit: dict[str, Any] = Field(default_factory=dict)
    contradiction_analysis: dict[str, Any] = Field(default_factory=dict)
    claims: list[ExtractedClaim]
    deduplication: list[DedupSelection]
    selected_section_ids: list[str]
    meta: ExtractionMetadata

    def to_legacy_dict(self, *, include_debug: bool = False) -> dict[str, Any]:
        claims = []
        for claim in self.claims:
            item = claim.model_dump(mode="json", exclude={"section_id"})
            claims.append(item)
        payload: dict[str, Any] = {
            "result": claims,
            "meta": self.meta.model_dump(mode="json"),
        }
        if self.contradiction_analysis:
            payload["contradiction_analysis"] = self.contradiction_analysis
        if self.deduplication_audit:
            payload["deduplication_audit"] = self.deduplication_audit
        if include_debug:
            payload["debug"] = {
                "step3_selection": [item.model_dump(mode="json") for item in self.deduplication],
            }
        return payload


class PipelineOptions(StrictModel):
    extraction_profile: Literal["implementation", "paper_assertions"] = "implementation"
    check_contradictions: bool = False
    review_cross_section_pairs: bool = False
    review_pair_counterevidence: bool = False
    contradiction_repository: Path | None = Field(default=None, exclude=True)
    pages_per_chunk: PositiveInt = 5
    pdf_parser: PdfParserName = "mistral-ocr"
    force_parser_refresh: bool = False
    marker: MarkerOptions = Field(default_factory=MarkerOptions)
    max_retries: PositiveInt = 5
    dedup_batch_size: int = Field(default=50, ge=2)


class PipelineResult(StrictModel):
    converted_document: ConvertedDocument
    sections: list[PaperSection]
    extraction: ClaimExtractionResult

    def to_legacy_dict(self, *, include_debug: bool = False) -> dict[str, Any]:
        return self.extraction.to_legacy_dict(include_debug=include_debug)


class LoadedClaimsArtifact(StrictModel):
    """Claims accepted for a resumed verification stage."""

    claims: list[dict[str, Any]]
    source_path: Path
    contradiction_analysis: dict[str, Any] = Field(default_factory=dict)
    source_format: Literal["typed", "legacy", "bare"]
    upstream_meta: dict[str, Any] = Field(default_factory=dict)


class LoadedSectionsArtifact(StrictModel):
    """Parsed sections accepted as a reusable claim-extraction input."""

    sections: list[PaperSection]
    source_path: Path
    source_format: Literal["bare", "envelope"]
    upstream_meta: dict[str, Any] = Field(default_factory=dict)
