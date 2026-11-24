"""Layout-aware paper parsing and standalone document graph construction."""

from .doc_geometry import (
    compute_reading_order_ranks,
    order_page_elements,
)
from .doc_graph import (
    build_document_graph,
    run_graph_building,
)
from .exceptions import (
    DescriptionError,
    LayoutDetectionError,
    PaperParsingError,
)
from .models import (
    PaperParsingOptions,
    PaperParsingResult,
)

__all__ = [
    "DescriptionError",
    "ImageDescription",
    "LayoutDetectionError",
    "LayoutExtractor",
    "PaperParsingError",
    "PaperParsingOptions",
    "PaperParsingPipeline",
    "PaperParsingResult",
    "StructuredPaperParser",
    "build_document_graph",
    "compute_reading_order_ranks",
    "order_page_elements",
    "run_graph_building",
]


def __getattr__(name: str):
    """Saved-graph consumers do not need the optional PDF/layout/VLM stack."""
    from importlib import import_module

    modules = {
        "LayoutExtractor": "doc_layout",
        "ImageDescription": "doc_ocr",
        "PaperParsingPipeline": "pipeline",
        "StructuredPaperParser": "structured_parser",
    }
    if name in modules:
        value = getattr(import_module(f"{__name__}.{modules[name]}"), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
