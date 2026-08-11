import builtins

import pytest

from osa_tool.operations.analysis.paper_claims import claim_validation
from osa_tool.operations.analysis.paper_claims.exceptions import ClaimExtractionError
from osa_tool.operations.analysis.paper_claims.claim_validation import (
    partition_valid_claim_candidates,
    validate_claim_candidate,
)
from tests.unit.operations.analysis.paper_claims.fixtures import (
    make_claim_candidate as make_candidate,
    make_paper_section as make_section,
)


def test_validate_claim_candidate_accepts_exact_source_text():
    candidate = make_candidate(
        claim="The model uses BERT-base without fine-tuning.",
        original_text="The model uses BERT-base without fine-tuning.",
    )

    validate_claim_candidate(candidate, section=make_section("The model uses BERT-base without fine-tuning."))

    assert candidate.original_text == "The model uses BERT-base without fine-tuning."


def test_validate_claim_candidate_repairs_minor_source_text_drift():
    source_text = (
        "Границу сегмента в нём задаёт не разметка, а само содержание: фрагмент обрывается там, "
        "где векторное представление текста резко меняется."
    )
    candidate = make_candidate(
        claim="Границу сегмента задаёт само содержание.",
        original_text=(
            "Граница сегмента в нём задаёт не разметка, а само содержание: фрагмент обрывается там, "
            "где векторное представление текста резко меняется."
        ),
        category="data_preprocessing",
    )

    validate_claim_candidate(candidate, section=make_section(source_text))

    assert candidate.original_text == source_text


def test_validate_claim_candidate_rejects_numeric_drift_in_fuzzy_evidence():
    source = "The measured significance threshold was 0.001 for every experiment in the evaluation."
    candidate = make_candidate(
        claim="The significance threshold was 0.01.",
        original_text="The measured significance threshold was 0.01 for every experiment in the evaluation.",
    )

    with pytest.raises(ValueError, match="original_text is not present"):
        validate_claim_candidate(candidate, section=make_section(source))


@pytest.mark.parametrize(
    ("source", "original_text"),
    [
        (
            "The retrieval pipeline does not use reranking for every production search result.",
            "The retrieval pipeline does use reranking for every production search result.",
        ),
        (
            "The retrieval pipeline keeps reranking disabled for every production search result.",
            "The retrieval pipeline keeps reranking enabled for every production search result.",
        ),
    ],
)
def test_validate_claim_candidate_rejects_polarity_or_word_drift_in_fuzzy_evidence(source, original_text):
    candidate = make_candidate(claim="The retrieval pipeline uses reranking.", original_text=original_text)

    with pytest.raises(ValueError, match="original_text is not present"):
        validate_claim_candidate(candidate, section=make_section(source))


def test_validate_claim_candidate_rejects_translation_from_devanagari():
    source = "यह मॉडल प्रशिक्षण के लिए बड़े डेटासेट का उपयोग करता है।"
    candidate = make_candidate(claim="The model uses a large training dataset.", original_text=source)

    with pytest.raises(ValueError, match="plausible language script"):
        validate_claim_candidate(candidate, section=make_section(source))


def test_partition_valid_claim_candidates_returns_errors_without_raising():
    section = make_section("The model uses BERT-base without fine-tuning.")
    valid_candidate = make_candidate(
        claim="The model uses BERT-base without fine-tuning.",
        original_text="The model uses BERT-base without fine-tuning.",
    )
    invalid_candidate = make_candidate(claim="Invented.", original_text="Invented sentence.")

    valid, invalid = partition_valid_claim_candidates([invalid_candidate, valid_candidate], section=section)

    assert valid == [valid_candidate]
    assert len(invalid) == 1
    assert "original_text is not present" in invalid[0]


def test_validate_claim_candidate_rejects_implausible_claim_script():
    candidate = make_candidate(
        claim="该模型使用BERT基础版，无需微调。",
        original_text="The model uses BERT-base without fine-tuning.",
    )

    with pytest.raises(ValueError, match="plausible language script"):
        validate_claim_candidate(
            candidate,
            section=make_section("The model uses BERT-base without fine-tuning."),
        )


def test_validate_claim_candidate_accepts_section_script_for_short_technical_evidence():
    source_text = (
        "Для генерации использовались следующие параметры модели. "
        "- Top-k: 50; "
        "Остальные параметры фиксировались на уровне эксперимента."
    )
    candidate = make_candidate(
        claim="Top-k генерации был зафиксирован на значении 50.",
        original_text="- Top-k: 50;",
        category="training_procedure",
    )

    validate_claim_candidate(candidate, section=make_section(source_text))

    assert candidate.original_text == "- Top-k: 50;"


def test_fuzzy_validation_explains_how_to_install_missing_rapidfuzz(monkeypatch):
    original_import = builtins.__import__

    def raise_for_rapidfuzz(name, *args, **kwargs):
        if name.startswith("rapidfuzz"):
            raise ImportError("missing rapidfuzz")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", raise_for_rapidfuzz)

    with pytest.raises(ClaimExtractionError, match=r'pip install "osa_tool\[paper-claims\]"'):
        claim_validation._load_rapidfuzz()
