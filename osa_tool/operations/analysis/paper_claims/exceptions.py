class PaperClaimsError(RuntimeError):
    """Base error for the paper-claims pipeline."""


class PdfInputError(PaperClaimsError):
    """Raised when a PDF input is missing or invalid."""


class PdfConversionError(PaperClaimsError):
    """Raised when PDF splitting or Marker conversion fails."""


class SectionParsingError(PaperClaimsError):
    """Raised when converted Markdown has no usable sections."""


class ClaimExtractionError(PaperClaimsError):
    """Raised when the LLM cannot produce a valid extraction result."""
