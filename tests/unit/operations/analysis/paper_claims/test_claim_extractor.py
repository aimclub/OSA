import json

import pytest

from osa_tool.operations.analysis.paper_claims.claim_extractor import ClaimExtractor
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


def test_claim_extraction_prompt_requires_verbatim_original_text():
    prompt = PromptLoader().get("paper_claims.claim_extraction_system")

    assert "`original_text` is evidence, not a paraphrase" in prompt
    assert "Copy it verbatim from the input section" in prompt


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
async def test_extract_accepts_pdf_hyphenated_line_break_source_text():
    source_text = (
        "В отличие от полностью закрытой LLM, RAG-система может обращаться к внешним источникам "
        "информации в ре-\n\nальном времени, и зависимость от статической параметрической памяти "
        "заметно снижается."
    )
    paper_section = section().model_copy(update={"text": source_text})
    candidate = {
        "claim": "RAG-система может обращаться к внешним источникам информации в реальном времени.",
        "original_text": (
            "В отличие от полностью закрытой LLM, RAG-система может обращаться к внешним источникам "
            "информации в ре-альном времени, и зависимость от статической параметрической памяти "
            "заметно снижается."
        ),
        "category": "model_architecture",
        "value": "RAG",
        "verifiability": "high",
    }
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            json.dumps([candidate], ensure_ascii=False),
            json.dumps(
                [
                    {
                        "claim_id": "c0001",
                        "claim": candidate["claim"],
                        "contradiction": False,
                    }
                ],
                ensure_ascii=False,
            ),
        ]
    )

    result = await ClaimExtractor(handler).extract([paper_section])

    assert result.claims[0].original_text == source_text
    assert "ре-\n\nальном" in result.claims[0].original_text
    assert len(handler.prompts) == 3


@pytest.mark.asyncio
async def test_extract_repairs_minor_original_text_word_drift_with_fuzzy_source_match():
    source_text = (
        "Границу сегмента в нём задаёт не разметка, а само содержание: фрагмент обрывается там, "
        "где векторное представление текста резко меняется."
    )
    paper_section = section().model_copy(update={"text": source_text})
    candidate = {
        "claim": "Границу сегмента задаёт само содержание.",
        "original_text": (
            "Граница сегмента в нём задаёт не разметка, а само содержание: фрагмент обрывается там, "
            "где векторное представление текста резко меняется."
        ),
        "category": "data_preprocessing",
        "value": None,
        "verifiability": "medium",
    }
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            json.dumps([candidate], ensure_ascii=False),
            json.dumps(
                [{"claim_id": "c0001", "claim": candidate["claim"], "contradiction": False}],
                ensure_ascii=False,
            ),
        ]
    )

    result = await ClaimExtractor(handler).extract([paper_section])

    assert result.claims[0].original_text == source_text
    assert len(handler.prompts) == 3


@pytest.mark.asyncio
async def test_extract_drops_ambiguous_fuzzy_original_text_after_final_attempt():
    source_text = (
        "The system uses version Y1 for retrieval embeddings and reranking in production. "
        "The system uses version Z1 for retrieval embeddings and reranking in production."
    )
    paper_section = section().model_copy(update={"text": source_text})
    candidate = {
        "claim": "The system uses version X1 for retrieval embeddings and reranking in production.",
        "original_text": "The system uses version X1 for retrieval embeddings and reranking in production.",
        "category": "infrastructure",
        "value": "X1",
        "verifiability": "high",
    }
    handler = FakeHandler(['[{"section_id":"s001"}]', json.dumps([candidate])])

    result = await ClaimExtractor(handler, max_retries=1).extract([paper_section])

    assert result.claims == []
    assert result.meta.step3_input_count == 0


@pytest.mark.asyncio
async def test_extract_accepts_russian_claim_for_short_latin_technical_evidence():
    source_text = (
        "Для генерации использовались следующие параметры модели. "
        "- Top-k: 50; "
        "Остальные параметры фиксировались на уровне эксперимента."
    )
    paper_section = section().model_copy(update={"text": source_text})
    candidate = {
        "claim": "Top-k генерации был зафиксирован на значении 50.",
        "original_text": "- Top-k: 50;",
        "category": "training_procedure",
        "value": "50",
        "verifiability": "high",
    }
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            json.dumps([candidate], ensure_ascii=False),
            json.dumps(
                [{"claim_id": "c0001", "claim": candidate["claim"], "contradiction": False}],
                ensure_ascii=False,
            ),
        ]
    )

    result = await ClaimExtractor(handler).extract([paper_section])

    assert result.claims[0].claim == candidate["claim"]
    assert result.claims[0].original_text == candidate["original_text"]


@pytest.mark.asyncio
async def test_extract_drops_bad_claim_after_retries_and_keeps_valid_claim():
    source_text = (
        "The model uses BERT-base without fine-tuning. " "The retrieval pipeline uses BM25 for candidate selection."
    )
    paper_section = section().model_copy(update={"text": source_text})
    valid_claim = {
        "claim": "The retrieval pipeline uses BM25 for candidate selection.",
        "original_text": "The retrieval pipeline uses BM25 for candidate selection.",
        "category": "model_architecture",
        "value": "BM25",
        "verifiability": "high",
    }
    bad_claim = {
        "claim": "该模型使用BERT基础版，无需微调。",
        "original_text": "The model uses BERT-base without fine-tuning.",
        "category": "model_architecture",
        "value": "BERT-base",
        "verifiability": "high",
    }
    repeated_bad_response = json.dumps([bad_claim, valid_claim], ensure_ascii=False)
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            repeated_bad_response,
            repeated_bad_response,
            json.dumps(
                [{"claim_id": "c0001", "claim": valid_claim["claim"], "contradiction": False}],
                ensure_ascii=False,
            ),
        ]
    )

    result = await ClaimExtractor(handler, max_retries=2).extract([paper_section])

    assert [claim.claim for claim in result.claims] == [valid_claim["claim"]]
    assert "plausible language script" in handler.prompts[2]


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
    assert "plausible language script" in handler.prompts[2]


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
async def test_extract_drops_claim_with_unmatched_source_text_after_final_attempt():
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            '[{"claim":"Invented","original_text":"Invented sentence.",'
            '"category":"model_architecture","value":null,"verifiability":"low"}]',
        ]
    )

    result = await ClaimExtractor(handler, max_retries=1).extract([section()])

    assert result.claims == []


@pytest.mark.asyncio
async def test_empty_section_selection_is_a_valid_empty_result():
    handler = FakeHandler(["[]"])
    handler.last_successful_model = "actual-model"
    result = await ClaimExtractor(handler).extract([section()], model="configured-model")

    assert result.claims == []
    assert result.deduplication == []
    assert result.selected_section_ids == []
    assert result.meta.model == "actual-model"
