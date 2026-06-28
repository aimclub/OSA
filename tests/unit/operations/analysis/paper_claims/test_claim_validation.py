import pytest

from osa_tool.operations.analysis.paper_claims.claim_schemas import ClaimCandidateResponse
from osa_tool.operations.analysis.paper_claims.claim_validation import (
    partition_valid_claim_candidates,
    validate_claim_candidate,
)
from osa_tool.operations.analysis.paper_claims.models import HeadingMeta, PaperSection


def make_section(text: str) -> PaperSection:
    return PaperSection(
        section_id="s001",
        name="Method",
        text=text,
        heading_meta=HeadingMeta(raw="2. Method", level=1, numbering="2"),
    )


def make_candidate(
    *,
    claim: str,
    original_text: str,
    category: str = "model_architecture",
) -> ClaimCandidateResponse:
    return ClaimCandidateResponse(
        claim=claim,
        original_text=original_text,
        category=category,
        value=None,
        verifiability="high",
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
        validate_claim_candidate(candidate, section=make_section("The model uses BERT-base without fine-tuning."))


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
