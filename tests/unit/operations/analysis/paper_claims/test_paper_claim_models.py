from osa_tool.operations.analysis.paper_claims.models import (
    ClaimExtractionResult,
    DedupSelection,
    ExtractedClaim,
    ExtractionMetadata,
)


def make_extraction_result() -> ClaimExtractionResult:
    return ClaimExtractionResult(
        claims=[
            ExtractedClaim(
                claim_id="c0001",
                claim="A claim.",
                original_text="A claim.",
                category="dataset",
                value=None,
                verifiability="high",
                section_id="s001",
                section_name="Method",
                section_heading_raw="1. Method",
            )
        ],
        deduplication=[DedupSelection(claim_id="c0001", claim="A claim.", contradiction=False)],
        selected_section_ids=["s001"],
        meta=ExtractionMetadata(
            source="paper.pdf",
            model="test",
            filtered_claims=1,
            step3_input_count=1,
            step3_output_count=1,
        ),
    )


def test_legacy_serialization_hides_debug_by_default():
    result = make_extraction_result()

    legacy = result.to_legacy_dict()

    assert set(legacy) == {"result", "meta"}
    assert legacy["result"][0]["claim_id"] == "c0001"
    assert "section_id" not in legacy["result"][0]
    assert "step3_selection" not in legacy
    assert "debug" not in legacy


def test_legacy_serialization_can_include_debug_step3_selection():
    result = make_extraction_result()

    legacy = result.to_legacy_dict(include_debug=True)

    assert set(legacy) == {"result", "meta", "debug"}
    assert legacy["debug"]["step3_selection"] == [{"claim_id": "c0001", "claim": "A claim.", "contradiction": False}]
