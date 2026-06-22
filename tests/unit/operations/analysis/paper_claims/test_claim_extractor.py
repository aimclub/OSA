import json

import pytest

from osa_tool.operations.analysis.paper_claims.claim_extractor import ClaimExtractor
from osa_tool.operations.analysis.paper_claims.exceptions import ClaimExtractionError
from osa_tool.operations.analysis.paper_claims.models import HeadingMeta, PaperSection
from osa_tool.utils.prompts_builder import PromptLoader


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


def test_section_filter_prompt_contains_valid_json_example():
    prompt = PromptLoader().get("paper_claims.section_filter_system")

    assert '- Example: [{"section_id":"s003"},{"section_id":"s004"}]' in prompt
    assert "[{section_id:s003}" not in prompt


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
async def test_extract_accepts_layout_only_source_text_differences():
    source_text = "The model uses BERT-\u200bbase\nwithout fine-tuning."
    paper_section = section().model_copy(update={"text": source_text})
    candidate = {
        "claim": "The model uses BERT-base without fine-tuning.",
        "original_text": "The model uses BERT-base without fine-tuning.",
        "category": "model_architecture",
        "value": "BERT-base",
        "verifiability": "high",
    }
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            json.dumps([candidate]),
            '[{"claim_id":"c0001","claim":"The model uses BERT-base without fine-tuning.",' '"contradiction":false}]',
        ]
    )

    result = await ClaimExtractor(handler).extract([paper_section])

    assert result.claims[0].original_text == source_text
    assert len(handler.prompts) == 3


@pytest.mark.asyncio
async def test_extract_repairs_claim_written_in_a_different_script():
    valid_claim = {
        "claim": "The model uses BERT-base without fine-tuning.",
        "original_text": "The model uses BERT-base without fine-tuning.",
        "category": "model_architecture",
        "value": "BERT-base",
        "verifiability": "high",
    }
    chinese_claim = {**valid_claim, "claim": "该模型使用BERT基础版，无需微调。"}
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            json.dumps([chinese_claim], ensure_ascii=False),
            json.dumps([valid_claim]),
            '[{"claim_id":"c0001","claim":"The model uses BERT-base without fine-tuning.",' '"contradiction":false}]',
        ]
    )

    result = await ClaimExtractor(handler, max_retries=2).extract([section()])

    assert result.claims[0].claim == valid_claim["claim"]
    assert "same language script" in handler.prompts[2]


@pytest.mark.asyncio
async def test_deduplication_repairs_rewritten_claim_text():
    valid_claim = {
        "claim": "The model uses BERT-base without fine-tuning.",
        "original_text": "The model uses BERT-base without fine-tuning.",
        "category": "model_architecture",
        "value": "BERT-base",
        "verifiability": "high",
    }
    correct_dedup = (
        '[{"claim_id":"c0001","claim":"The model uses BERT-base without fine-tuning.",' '"contradiction":false}]'
    )
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            json.dumps([valid_claim]),
            '[{"claim_id":"c0001","claim":"Das Modell verwendet BERT-base ohne Feinabstimmung.",'
            '"contradiction":false}]',
            correct_dedup,
        ]
    )

    result = await ClaimExtractor(handler, max_retries=2).extract([section()])

    assert result.deduplication[0].claim == valid_claim["claim"]
    assert "copy claim text verbatim" in handler.prompts[3]


@pytest.mark.asyncio
async def test_source_text_error_includes_section_preview():
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            '[{"claim":"Invented","original_text":"Invented sentence.",'
            '"category":"model_architecture","value":null,"verifiability":"low"}]',
        ]
    )

    with pytest.raises(ClaimExtractionError, match="section_text_preview=.*The model uses BERT-base"):
        await ClaimExtractor(handler, max_retries=1).extract([section()])


@pytest.mark.asyncio
async def test_empty_section_selection_is_a_valid_empty_result():
    handler = FakeHandler(["[]"])
    handler.last_successful_model = "actual-model"
    result = await ClaimExtractor(handler).extract([section()], model="configured-model")

    assert result.claims == []
    assert result.deduplication == []
    assert result.selected_section_ids == []
    assert result.meta.model == "actual-model"
