from osa_tool.operations.analysis.paper_claims.models import (
    ClaimExtractionResult,
    DedupSelection,
    ExtractedClaim,
    ExtractionMetadata,
)


def test_legacy_serialization_preserves_mvp_shape():
    result = ClaimExtractionResult(
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

    legacy = result.to_legacy_dict()

    assert set(legacy) == {"result", "step3_selection", "meta"}
    assert legacy["result"][0]["claim_id"] == "c0001"
    assert "section_id" not in legacy["result"][0]
