from osa_tool.operations.analysis.paper_claims.claim_extractor import ClaimExtractor
from osa_tool.operations.analysis.paper_claims.io import (
    export_loaded_claims,
    export_section_extraction,
    load_claims_json,
    load_sections_json,
)
from osa_tool.operations.analysis.paper_claims.models import (
    ClaimExtractionResult,
    ConvertedDocument,
    LoadedClaimsArtifact,
    LoadedSectionsArtifact,
    PaperSection,
    PipelineOptions,
    PipelineResult,
)
from osa_tool.operations.analysis.paper_claims.section_extractor import (
    extract_claims_from_sections,
    run_claim_extraction_from_sections,
)

__all__ = [
    "ClaimExtractor",
    "ClaimExtractionResult",
    "ConvertedDocument",
    "LoadedClaimsArtifact",
    "LoadedSectionsArtifact",
    "MarkerDocumentConverter",
    "MarkdownSectionParser",
    "PaperClaimPipeline",
    "PaperSection",
    "PdfChunker",
    "PipelineOptions",
    "PipelineResult",
    "clear_marker_cache",
    "export_loaded_claims",
    "export_section_extraction",
    "extract_claims_from_sections",
    "load_claims_json",
    "load_sections_json",
    "run_claim_extraction_from_sections",
]


def __getattr__(name: str):
    """Keep PDF/Marker helpers lazy so parsed-section users avoid PDF dependencies."""
    if name in {"MarkerDocumentConverter", "clear_marker_cache"}:
        from osa_tool.operations.analysis.paper_claims.marker_converter import (
            MarkerDocumentConverter,
            clear_marker_cache,
        )

        return {"MarkerDocumentConverter": MarkerDocumentConverter, "clear_marker_cache": clear_marker_cache}[name]
    if name == "MarkdownSectionParser":
        from osa_tool.operations.analysis.paper_claims.section_parser import MarkdownSectionParser

        return MarkdownSectionParser
    if name == "PdfChunker":
        from osa_tool.operations.analysis.paper_claims.pdf_splitter import PdfChunker

        return PdfChunker
    if name == "PaperClaimPipeline":
        from osa_tool.operations.analysis.paper_claims.pipeline import PaperClaimPipeline

        return PaperClaimPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
