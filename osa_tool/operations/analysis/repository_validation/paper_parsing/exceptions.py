class PaperParsingError(RuntimeError):
    """Base error for the paper-parsing pipeline."""


class LayoutDetectionError(PaperParsingError):
    """Raised when layout detection produces no usable elements."""


class DescriptionError(PaperParsingError):
    """Raised when every VLM description request fails."""
