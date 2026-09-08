class PaperParsingError(RuntimeError):
    """Base error for the paper-parsing pipeline."""


class LayoutDetectionError(PaperParsingError):
    """Raised when layout detection produces no usable elements."""


class DescriptionError(PaperParsingError):
    """Raised when every VLM description request fails."""


class PageRenderError(PaperParsingError):
    """Raised when a document's pages cannot be rasterized or read back."""
