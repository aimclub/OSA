import json
from types import SimpleNamespace

import pytest

from osa_tool.operations.analysis.paper_claims import claim_validation
from osa_tool.operations.analysis.paper_claims.claim_extractor import ClaimExtractor
from osa_tool.operations.analysis.paper_claims.models import HeadingMeta, PaperSection
from osa_tool.utils.prompts_builder import PromptLoader
from tests.unit.operations.analysis.paper_claims.fixtures import (
    FakeAsyncHandler as FakeHandler,
    ModelTrackingFakeHandler,
    make_extracted_claim as extracted_claim,
    make_paper_section as section,
    word_token_count as fake_token_count,
)


def test_section_filter_prompt_contains_valid_json_example():
    prompt = PromptLoader().get("paper_claims.section_filter_system")

    assert '- Example: [{"section_id":"s003"},{"section_id":"s004"}]' in prompt
    assert "[{section_id:s003}" not in prompt


def test_section_filter_prompt_excludes_glossary_and_preliminaries_sections():
    prompt = PromptLoader().get("paper_claims.section_filter_system")

    assert "List of Abbreviations and Symbols" in prompt
    assert "Preliminaries" in prompt


def test_claim_extraction_prompt_requires_verbatim_original_text():
    prompt = PromptLoader().get("paper_claims.claim_extraction_system")

    assert "`original_text` is evidence, not a paraphrase" in prompt
    assert "Copy it verbatim from the input section" in prompt


def test_claim_extraction_prompt_excludes_acronym_definitions():
    prompt = PromptLoader().get("paper_claims.claim_extraction_system")

    assert "acronym/abbreviation expansions" in prompt
    assert "JSON stands for JavaScript Object Notation" in prompt
    assert "GPU stands for Graphics Processing Unit" in prompt


def test_deduplication_prompt_forbids_empty_output_for_non_empty_input():
    prompt = PromptLoader().get("paper_claims.deduplication_system")

    assert "If the input array is empty, return []" in prompt
    assert "If the input array is non-empty, never return []" in prompt
    assert "fully deduplicated to zero claims" not in prompt


def test_claim_extractor_rejects_dedup_batch_size_below_two():
    with pytest.raises(ValueError, match="at least 2"):
        ClaimExtractor(FakeHandler([]), dedup_batch_size=1)


def test_repair_prompt_is_bounded_to_model_input_budget(monkeypatch):
    def fake_count_tokens(text, _encoder="fake"):
        return len(text.split())

    def fake_truncate_to_tokens(text, max_tokens, _encoder="fake", mode="start"):
        words = text.split()
        if len(words) <= max_tokens:
            return text
        if mode == "middle-out":
            half = max_tokens // 2
            return " ".join(words[:half] + words[-half:])
        return " ".join(words[:max_tokens])

    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_claims.claim_extractor.count_tokens",
        fake_count_tokens,
    )
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_claims.claim_input_planner.count_tokens",
        fake_count_tokens,
    )
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_claims.claim_extractor.truncate_to_tokens",
        fake_truncate_to_tokens,
    )
    handler = FakeHandler([])
    handler.model_settings = SimpleNamespace(context_window=500, max_tokens=50, encoder="fake")
    extractor = ClaimExtractor(handler)

    prompt = extractor._repair_prompt(
        error="Validation error: original_text is missing",
        response="response " * 1000,
        original_prompt="original " * 1000,
        system="system",
    )
    budget, _encoder = extractor._input_planner.input_token_budget("system")

    assert "Validation error: original_text is missing" in prompt
    assert fake_count_tokens(prompt) <= budget


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
async def test_extract_preserves_verbatim_evidence_with_json_like_words(monkeypatch):
    source_text = "The flag is True."
    candidate = {
        "claim": source_text,
        "original_text": source_text,
        "category": "infrastructure",
        "value": "True",
        "verifiability": "high",
    }

    def fail_fuzzy_match(*_args, **_kwargs):
        raise AssertionError("exact original_text must not require fuzzy repair")

    monkeypatch.setattr(claim_validation, "_find_fuzzy_source_match", fail_fuzzy_match)
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            json.dumps([candidate]),
            json.dumps([{"claim_id": "c0001", "claim": source_text, "contradiction": False}]),
        ]
    )

    result = await ClaimExtractor(handler).extract([section(source_text)])

    assert result.claims[0].claim == source_text
    assert result.claims[0].original_text == source_text
    assert result.claims[0].value == "True"


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
    assert len(handler.prompts) == 3


@pytest.mark.asyncio
async def test_extract_accepts_formula_source_text_with_minor_case_drift():
    formula = r"$$CTR = \frac{1}{T} \sum_{t=1}^{T} \mathbf{1}[H_t(T_t) = True].$$"
    source_text = (
        "Confirming Test Rate (CTR) is defined as the share of turns where the hypothesis predicts True:\n\n"
        f"{formula}\n"
        "(2.4)"
    )
    paper_section = section().model_copy(update={"text": source_text})
    candidate = {
        "claim": "CTR is computed as the average indicator that H_t(T_t) is True.",
        "original_text": r"$$CTR = \frac{1}{T} \sum_{t=1}^{T} \mathbf{1}[H_t(T_t) = true].$$",
        "category": "evaluation_metric",
        "value": "CTR",
        "verifiability": "high",
    }
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            json.dumps([candidate]),
            json.dumps(
                [{"claim_id": "c0001", "claim": candidate["claim"], "contradiction": False}],
                ensure_ascii=False,
            ),
        ]
    )

    result = await ClaimExtractor(handler).extract([paper_section])

    assert result.claims[0].original_text == formula


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
                [
                    {
                        "claim_id": "c0001",
                        "claim": valid_claim["claim"],
                        "contradiction": False,
                    }
                ],
                ensure_ascii=False,
            ),
        ]
    )

    result = await ClaimExtractor(handler, max_retries=2).extract([paper_section])

    assert [claim.claim for claim in result.claims] == [valid_claim["claim"]]
    assert "plausible language script" in handler.prompts[2]


@pytest.mark.asyncio
async def test_extract_drops_blank_candidate_after_retry_and_keeps_valid_claim():
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
    blank_claim = {**valid_claim, "claim": "", "original_text": ""}
    repeated_response = json.dumps([blank_claim, valid_claim])
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            repeated_response,
            repeated_response,
            json.dumps([{"claim_id": "c0001", "claim": valid_claim["claim"], "contradiction": False}]),
        ]
    )

    result = await ClaimExtractor(handler, max_retries=2).extract([paper_section])

    assert [claim.claim for claim in result.claims] == [valid_claim["claim"]]
    assert "schema validation failed" in handler.prompts[2]


@pytest.mark.asyncio
async def test_extract_skips_failed_section_and_keeps_document_claims():
    sections = [
        PaperSection(
            section_id="s001",
            name="Method",
            text="The pipeline stores extracted claims as JSON files.",
            heading_meta=HeadingMeta(raw="2. Method", level=1, numbering="2"),
        ),
        PaperSection(
            section_id="s002",
            name="Metrics",
            text="The metric section contains malformed LLM output in this test.",
            heading_meta=HeadingMeta(raw="3. Metrics", level=1, numbering="3"),
        ),
    ]
    valid_claim = {
        "claim": "The pipeline stores extracted claims as JSON files.",
        "original_text": "The pipeline stores extracted claims as JSON files.",
        "category": "infrastructure",
        "value": "JSON",
        "verifiability": "high",
    }
    handler = FakeHandler(
        [
            '[{"section_id":"s001"},{"section_id":"s002"}]',
            json.dumps([valid_claim]),
            "not json",
            "still not json",
            json.dumps(
                [{"claim_id": "c0001", "claim": valid_claim["claim"], "contradiction": False}],
                ensure_ascii=False,
            ),
        ]
    )

    result = await ClaimExtractor(handler, max_retries=2).extract(sections)

    assert [claim.claim for claim in result.claims] == [valid_claim["claim"]]
    assert result.meta.step3_input_count == 1
    assert result.meta.step3_output_count == 1


@pytest.mark.asyncio
async def test_extract_skips_section_when_model_request_raises_and_keeps_document_claims():
    sections = [
        PaperSection(
            section_id="s001",
            name="Method",
            text="The pipeline stores extracted claims as JSON files.",
            heading_meta=HeadingMeta(raw="2. Method", level=1, numbering="2"),
        ),
        PaperSection(
            section_id="s002",
            name="Metrics",
            text="The model request raises for this section.",
            heading_meta=HeadingMeta(raw="3. Metrics", level=1, numbering="3"),
        ),
    ]
    valid_claim = {
        "claim": "The pipeline stores extracted claims as JSON files.",
        "original_text": "The pipeline stores extracted claims as JSON files.",
        "category": "infrastructure",
        "value": "JSON",
        "verifiability": "high",
    }
    handler = FakeHandler(
        [
            '[{"section_id":"s001"},{"section_id":"s002"}]',
            json.dumps([valid_claim]),
            RuntimeError("provider outage"),
            json.dumps(
                [{"claim_id": "c0001", "claim": valid_claim["claim"], "contradiction": False}],
                ensure_ascii=False,
            ),
        ]
    )

    result = await ClaimExtractor(handler, max_retries=2).extract(sections)

    assert [claim.claim for claim in result.claims] == [valid_claim["claim"]]
    assert result.meta.step3_input_count == 1
    assert result.meta.step3_output_count == 1


@pytest.mark.asyncio
async def test_extract_splits_long_section_before_sending_claim_requests(monkeypatch):
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_claims.claim_input_planner.count_tokens",
        fake_token_count,
    )
    long_text = ". ".join(" ".join(f"token{i}_{word}" for word in range(35)) for i in range(8)) + "."
    paper_section = section().model_copy(update={"text": long_text})
    handler = FakeHandler(['[{"section_id":"s001"}]'] + ["[]"] * 20)
    claim_system = PromptLoader().get("paper_claims.claim_extraction_system")
    handler.model_settings = SimpleNamespace(
        context_window=fake_token_count(claim_system) + 100 + 256 + 512 + 80,
        max_tokens=100,
        encoder="fake",
    )

    result = await ClaimExtractor(handler).extract([paper_section])

    extraction_prompts = handler.prompts[1:]
    assert result.claims == []
    assert len(extraction_prompts) > 1
    assert all(long_text not in prompt for prompt in extraction_prompts)


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
async def test_extract_records_claim_extraction_model_not_later_dedup_model():
    valid_claim = {
        "claim": "The model uses BERT-base without fine-tuning.",
        "original_text": "The model uses BERT-base without fine-tuning.",
        "category": "model_architecture",
        "value": "BERT-base",
        "verifiability": "high",
    }
    handler = ModelTrackingFakeHandler(
        [
            '[{"section_id":"s001"}]',
            json.dumps([valid_claim]),
            '[{"claim_id":"c0001","claim":"The model uses BERT-base without fine-tuning.",' '"contradiction":false}]',
        ],
        models=["section-selector-model", "claim-extraction-model", "dedup-fallback-model"],
    )

    result = await ClaimExtractor(handler).extract([section()])

    assert result.meta.model == "claim-extraction-model"
    assert handler.last_successful_model == "dedup-fallback-model"


@pytest.mark.asyncio
async def test_deduplication_repairs_empty_response_for_non_empty_input():
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
            "[]",
            correct_dedup,
        ]
    )

    result = await ClaimExtractor(handler, max_retries=2).extract([section()])

    assert len(result.claims) == 1
    assert "Deduplication returned 0 claims" in handler.prompts[3]


@pytest.mark.asyncio
async def test_deduplication_falls_back_after_retries_and_keeps_original_claims():
    source_text = "The pipeline uses chunked PDF processing. " "The pipeline caches Marker Markdown output."
    paper_section = section().model_copy(update={"text": source_text})
    candidates = [
        {
            "claim": "The pipeline uses chunked PDF processing.",
            "original_text": "The pipeline uses chunked PDF processing.",
            "category": "data_preprocessing",
            "value": None,
            "verifiability": "high",
        },
        {
            "claim": "The pipeline caches Marker Markdown output.",
            "original_text": "The pipeline caches Marker Markdown output.",
            "category": "infrastructure",
            "value": "Marker Markdown",
            "verifiability": "high",
        },
    ]
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            json.dumps(candidates),
            "[]",
        ]
    )

    result = await ClaimExtractor(handler, max_retries=1).extract([paper_section])

    assert [claim.claim_id for claim in result.claims] == ["c0001", "c0002"]
    assert [item.claim_id for item in result.deduplication] == ["c0001", "c0002"]
    assert all(item.contradiction is False for item in result.deduplication)
    assert result.meta.step3_input_count == 2
    assert result.meta.step3_output_count == 2


@pytest.mark.asyncio
async def test_batched_deduplication_sends_multiple_requests_and_preserves_order():
    source_text = (
        "The pipeline splits PDFs into chunks. "
        "The pipeline converts chunks with Marker. "
        "The pipeline parses Markdown into sections."
    )
    paper_section = section().model_copy(update={"text": source_text})
    candidates = [
        {
            "claim": "The pipeline splits PDFs into chunks.",
            "original_text": "The pipeline splits PDFs into chunks.",
            "category": "data_preprocessing",
            "value": None,
            "verifiability": "high",
        },
        {
            "claim": "The pipeline converts chunks with Marker.",
            "original_text": "The pipeline converts chunks with Marker.",
            "category": "infrastructure",
            "value": "Marker",
            "verifiability": "high",
        },
        {
            "claim": "The pipeline parses Markdown into sections.",
            "original_text": "The pipeline parses Markdown into sections.",
            "category": "data_preprocessing",
            "value": "Markdown",
            "verifiability": "high",
        },
    ]
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            json.dumps(candidates),
            json.dumps(
                [
                    {
                        "claim_id": "c0001",
                        "claim": candidates[0]["claim"],
                        "contradiction": False,
                    },
                    {
                        "claim_id": "c0002",
                        "claim": candidates[1]["claim"],
                        "contradiction": False,
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "claim_id": "c0003",
                        "claim": candidates[2]["claim"],
                        "contradiction": False,
                    }
                ]
            ),
            json.dumps(
                [
                    {
                        "claim_id": "c0001",
                        "claim": candidates[0]["claim"],
                        "contradiction": False,
                    },
                    {
                        "claim_id": "c0002",
                        "claim": candidates[1]["claim"],
                        "contradiction": False,
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "claim_id": "c0001",
                        "claim": candidates[0]["claim"],
                        "contradiction": False,
                    },
                    {
                        "claim_id": "c0003",
                        "claim": candidates[2]["claim"],
                        "contradiction": False,
                    },
                ]
            ),
            json.dumps(
                [
                    {
                        "claim_id": "c0002",
                        "claim": candidates[1]["claim"],
                        "contradiction": False,
                    },
                    {
                        "claim_id": "c0003",
                        "claim": candidates[2]["claim"],
                        "contradiction": False,
                    },
                ]
            ),
        ]
    )

    result = await ClaimExtractor(handler, dedup_batch_size=2).extract([paper_section])

    assert [claim.claim_id for claim in result.claims] == ["c0001", "c0002", "c0003"]
    assert len(handler.prompts) == 7
    assert '"claim_id": "c0001"' in handler.prompts[2]
    assert '"claim_id": "c0003"' in handler.prompts[3]


@pytest.mark.asyncio
async def test_global_deduplication_compares_duplicate_survivors_across_batch_boundaries():
    source_text = (
        "The pipeline splits PDFs into chunks. "
        "The pipeline caches Marker Markdown output. "
        "The pipeline caches Marker Markdown output."
    )
    paper_section = section().model_copy(update={"text": source_text})
    candidates = [
        {
            "claim": "The pipeline splits PDFs into chunks.",
            "original_text": "The pipeline splits PDFs into chunks.",
            "category": "data_preprocessing",
            "value": None,
            "verifiability": "high",
        },
        {
            "claim": "The pipeline caches Marker Markdown output.",
            "original_text": "The pipeline caches Marker Markdown output.",
            "category": "infrastructure",
            "value": "Marker Markdown",
            "verifiability": "high",
        },
        {
            "claim": "The pipeline caches Marker Markdown output.",
            "original_text": "The pipeline caches Marker Markdown output.",
            "category": "infrastructure",
            "value": "Marker Markdown",
            "verifiability": "high",
        },
    ]
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            json.dumps(candidates),
            json.dumps(
                [
                    {"claim_id": "c0001", "claim": candidates[0]["claim"], "contradiction": False},
                    {"claim_id": "c0002", "claim": candidates[1]["claim"], "contradiction": False},
                ]
            ),
            json.dumps([{"claim_id": "c0003", "claim": candidates[2]["claim"], "contradiction": False}]),
            json.dumps(
                [
                    {"claim_id": "c0001", "claim": candidates[0]["claim"], "contradiction": False},
                    {"claim_id": "c0002", "claim": candidates[1]["claim"], "contradiction": False},
                ]
            ),
            json.dumps(
                [
                    {"claim_id": "c0001", "claim": candidates[0]["claim"], "contradiction": False},
                    {"claim_id": "c0003", "claim": candidates[2]["claim"], "contradiction": False},
                ]
            ),
            json.dumps([{"claim_id": "c0002", "claim": candidates[1]["claim"], "contradiction": False}]),
        ]
    )

    result = await ClaimExtractor(handler, dedup_batch_size=2).extract([paper_section])

    assert [claim.claim_id for claim in result.claims] == ["c0001", "c0002"]
    assert [claim.claim for claim in result.claims] == [
        "The pipeline splits PDFs into chunks.",
        "The pipeline caches Marker Markdown output.",
    ]


@pytest.mark.asyncio
async def test_failed_deduplication_batch_does_not_erase_successful_batches():
    source_text = (
        "The pipeline splits PDFs into chunks. "
        "The pipeline converts chunks with Marker. "
        "The pipeline parses Markdown into sections."
    )
    paper_section = section().model_copy(update={"text": source_text})
    candidates = [
        {
            "claim": "The pipeline splits PDFs into chunks.",
            "original_text": "The pipeline splits PDFs into chunks.",
            "category": "data_preprocessing",
            "value": None,
            "verifiability": "high",
        },
        {
            "claim": "The pipeline converts chunks with Marker.",
            "original_text": "The pipeline converts chunks with Marker.",
            "category": "infrastructure",
            "value": "Marker",
            "verifiability": "high",
        },
        {
            "claim": "The pipeline parses Markdown into sections.",
            "original_text": "The pipeline parses Markdown into sections.",
            "category": "data_preprocessing",
            "value": "Markdown",
            "verifiability": "high",
        },
    ]
    handler = FakeHandler(
        [
            '[{"section_id":"s001"}]',
            json.dumps(candidates),
            json.dumps(
                [
                    {
                        "claim_id": "c0001",
                        "claim": candidates[0]["claim"],
                        "contradiction": False,
                    },
                    {
                        "claim_id": "c0002",
                        "claim": candidates[1]["claim"],
                        "contradiction": False,
                    },
                ]
            ),
            "[]",
            json.dumps(
                [
                    {"claim_id": "c0001", "claim": candidates[0]["claim"], "contradiction": False},
                    {"claim_id": "c0002", "claim": candidates[1]["claim"], "contradiction": False},
                ]
            ),
            json.dumps(
                [
                    {"claim_id": "c0001", "claim": candidates[0]["claim"], "contradiction": False},
                    {"claim_id": "c0003", "claim": candidates[2]["claim"], "contradiction": False},
                ]
            ),
            json.dumps(
                [
                    {"claim_id": "c0002", "claim": candidates[1]["claim"], "contradiction": False},
                    {"claim_id": "c0003", "claim": candidates[2]["claim"], "contradiction": False},
                ]
            ),
        ]
    )

    result = await ClaimExtractor(handler, max_retries=1, dedup_batch_size=2).extract([paper_section])

    assert [claim.claim_id for claim in result.claims] == ["c0001", "c0002", "c0003"]
    assert [item.claim_id for item in result.deduplication] == [
        "c0001",
        "c0002",
        "c0003",
    ]


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
