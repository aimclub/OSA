from collections.abc import Iterable

from osa_tool.operations.analysis.paper_claims.claim_schemas import ClaimCandidateResponse
from osa_tool.operations.analysis.paper_claims.models import ExtractedClaim, HeadingMeta, PaperSection

DEFAULT_SECTION_TEXT = "The model uses BERT-base without fine-tuning."


class FakeAsyncHandler:
    """Queued async LLM handler used by paper-claims unit tests."""

    def __init__(self, responses: Iterable[str | BaseException]):
        self.responses = iter(responses)
        self.prompts: list[str] = []

    async def async_request(self, prompt, system_message=None, retry_delay=1):
        self.prompts.append(prompt)
        response = next(self.responses)
        if isinstance(response, BaseException):
            raise response
        return response


class ModelTrackingFakeHandler(FakeAsyncHandler):
    """Fake handler that records the model producing each successful response."""

    def __init__(self, responses: Iterable[str | BaseException], models: Iterable[str]):
        super().__init__(responses)
        self.models = iter(models)
        self.last_successful_model: str | None = None

    async def async_request(self, prompt, system_message=None, retry_delay=1):
        response = await super().async_request(prompt, system_message, retry_delay)
        self.last_successful_model = next(self.models)
        return response


def word_token_count(text: str, _encoder: str = "fake") -> int:
    return len(text.split())


def make_paper_section(
    text: str = DEFAULT_SECTION_TEXT,
    *,
    section_id: str = "s001",
    name: str = "Method",
    heading_raw: str = "2. Method",
    heading_level: int = 1,
    heading_numbering: str | None = "2",
) -> PaperSection:
    return PaperSection(
        section_id=section_id,
        name=name,
        text=text,
        heading_meta=HeadingMeta(raw=heading_raw, level=heading_level, numbering=heading_numbering),
    )


def make_extracted_claim(
    claim_id: str,
    claim: str,
    *,
    original_text: str | None = None,
    category: str = "infrastructure",
    value: str | None = None,
    verifiability: str = "high",
    section_id: str = "s001",
    section_name: str = "Method",
    section_heading_raw: str | None = "2. Method",
    contradiction: bool = False,
) -> ExtractedClaim:
    return ExtractedClaim(
        claim_id=claim_id,
        claim=claim,
        original_text=claim if original_text is None else original_text,
        category=category,
        value=value,
        verifiability=verifiability,
        section_id=section_id,
        section_name=section_name,
        section_heading_raw=section_heading_raw,
        contradiction=contradiction,
    )


def make_claim_candidate(
    *,
    claim: str,
    original_text: str,
    category: str = "model_architecture",
    value: str | None = None,
    verifiability: str = "high",
) -> ClaimCandidateResponse:
    return ClaimCandidateResponse(
        claim=claim,
        original_text=original_text,
        category=category,
        value=value,
        verifiability=verifiability,
    )
