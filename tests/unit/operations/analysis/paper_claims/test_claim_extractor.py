import json

import pytest

from osa_tool.operations.analysis.paper_claims.claim_extractor import ClaimExtractor
from osa_tool.operations.analysis.paper_claims.models import HeadingMeta, PaperSection


class FakeHandler:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.prompts = []

    async def async_request(self, prompt, system_message=None, retry_delay=1):
        self.prompts.append(prompt)
        return next(self.responses)


def section() -> PaperSection:
    return PaperSection(
        section_id="s001",
        name="Method",
        text="The model uses BERT-base without fine-tuning.",
        heading_meta=HeadingMeta(raw="2. Method", level=1, numbering="2"),
    )


@pytest.mark.asyncio
async def test_extract_repairs_invalid_source_text_and_deduplicates():
    valid_claim = {
        "claim": "The model uses BERT-base without fine-tuning.",
        "original_text": "The model uses BERT-base without fine-tuning.",
        "category": "model_architecture",
        "value": "BERT-base",
        "verifiability": "high",
    }
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            json.dumps([{**valid_claim, "original_text": "invented sentence"}]),
            json.dumps([valid_claim]),
            '[{"claim_id":"c0001","claim":"The model uses BERT-base without fine-tuning.",' '"contradiction":false}]',
        ]
    )

    result = await ClaimExtractor(handler, max_retries=2).extract([section()], source="paper.pdf", model="test")

    assert len(result.claims) == 1
    assert result.claims[0].section_name == "Method"
    assert result.meta.filtered_claims == 1
    assert "Validation error" in handler.prompts[2]


@pytest.mark.asyncio
async def test_empty_section_selection_is_a_valid_empty_result():
    result = await ClaimExtractor(FakeHandler(["[]"])).extract([section()])

    assert result.claims == []
    assert result.deduplication == []
    assert result.selected_section_ids == []
