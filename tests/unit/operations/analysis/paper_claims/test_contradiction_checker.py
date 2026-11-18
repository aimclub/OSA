import json
import subprocess

import pytest

from osa_tool.operations.analysis.paper_claims.claim_extractor import ClaimExtractor
from osa_tool.operations.analysis.paper_claims.contradiction_checker import ContradictionChecker
from osa_tool.operations.analysis.paper_claims.contradiction_checker import attach_contradiction_links
from osa_tool.operations.analysis.paper_claims.io import load_claims_json
from tests.unit.operations.analysis.paper_claims.fixtures import FakeAsyncHandler, make_extracted_claim, make_paper_section


def checker(handler):
    return ContradictionChecker(ClaimExtractor(handler, max_retries=1, show_progress=False)._request_validated)


def claims():
    return [make_extracted_claim("a", "The model achieves 90 percent accuracy on validation.", original_text="Accuracy was 90."),
            make_extracted_claim("b", "The model achieves 95 percent accuracy on validation.", original_text="Accuracy was 95.")]


@pytest.mark.asyncio
async def test_section_pipeline_sends_pinned_source_to_pair_reviewer(tmp_path, monkeypatch):
    from unittest.mock import AsyncMock
    from osa_tool.operations.analysis.paper_claims.models import PipelineOptions
    from osa_tool.operations.analysis.paper_claims.section_extractor import extract_claims_from_sections

    def git(*args):
        return subprocess.check_output(["git", "-C", str(tmp_path), *args], text=True).strip()

    git("init", "-q")
    source = tmp_path / "evaluation.py"
    source.write_text("accuracy = 0.90\n", encoding="utf8")
    git("add", "evaluation.py")
    git("-c", "user.name=Test", "-c", "user.email=test@example.org", "commit", "-qm", "fixture")
    revision = git("rev-parse", "HEAD")
    source.write_text("accuracy = 0.12\n", encoding="utf8")
    monkeypatch.setattr(ClaimExtractor, "_step_1_select_sections", AsyncMock(return_value=["s001"]))
    monkeypatch.setattr(ClaimExtractor, "_step_2_extract_claims", AsyncMock(return_value=claims()))
    monkeypatch.setattr(ClaimExtractor, "_step_3_deduplicate_claims", AsyncMock(return_value=(claims(), [])))
    evidence_id = f"{revision}:evaluation.py:1"
    decision = dict(pair_id="p0000", status="contradiction", issue_type="numerical", reason="Same conditions.",
                    evidence_ids=["a#source0", "b#source0", evidence_id], left_claim_quote="90 percent",
                    right_claim_quote="95 percent")
    handler = FakeAsyncHandler([json.dumps([decision])])
    result = await extract_claims_from_sections(handler, [make_paper_section()],
                    PipelineOptions(check_contradictions=True, contradiction_repository=tmp_path))
    pair = result.contradiction_analysis["candidate_pairs"][0]
    assert pair["repository_context"][0]["snippet"] == "accuracy = 0.90"
    assert pair["repository_context"][0]["evidence_id"] == evidence_id
    assert result.claims[0].contradicts_claim_ids == ["b"]


def test_source_component_links_connect_calls_without_shared_words():
    items = [
        make_extracted_claim("declaration", "The algorithm uses a decoder.",
                             original_text="Input: encoder E, decoder D"),
        make_extracted_claim("caption", "Figure 2 shows a component.",
                             original_text="Figure 2: Context block in Decoder."),
        make_extracted_claim("diagram", "The Context block labels its inputs u and v."),
        make_extracted_claim("call", "The result is D(z, u, v)."),
        make_extracted_claim("other", "The result is E(z, u, v)."),
        make_extracted_claim("substring", "The result is RED(z, u, v)."),
        make_extracted_claim("caption_only", "Figure 2 depicts the Context block."),
    ]
    c = checker(FakeAsyncHandler([]))
    before = [x.model_dump() for x in items]
    rows, coverage = c.plan(items)
    linked = [r for r in rows if r.get("retrieval_route") == "source_component_link"]
    assert [(r["left"]["claim_id"], r["right"]["claim_id"]) for r in linked] == [("diagram", "call")]
    assert {r["relation"] for r in linked[0]["relation_context"]} == {"part_of", "alias"}
    assert coverage["relation_candidates"] == 1
    assert before == [x.model_dump() for x in items]
    c.use_component_links = False
    assert not c.plan(items)[1]["relation_candidates"]


def test_ambiguous_symbols_and_ungrounded_claim_links_are_not_expanded():
    items = [
        make_extracted_claim("a", "Input: decoder D", original_text="No symbol declaration."),
        make_extracted_claim("b", "Figure 2: Context block in Decoder.", original_text="No caption."),
        make_extracted_claim("c", "The Context block labels its inputs u and v."),
        make_extracted_claim("d", "The result is D(z, u, v)."),
    ]
    c = checker(FakeAsyncHandler([]))
    assert c.plan(items)[1]["relation_candidates"] == 0
    items[0].original_text = "Input: decoder D, discriminator D"
    items[1].original_text = "Figure 2: Context block in Decoder."
    assert c.plan(items)[1]["relation_candidates"] == 0


def test_component_link_quota_leaves_room_for_lexical_pairs():
    items = [
        make_extracted_claim("declaration", "An algorithm.",
                             original_text="Input: decoder D"),
        make_extracted_claim("caption", "A caption.",
                             original_text="Figure 2: Context block in Decoder."),
        make_extracted_claim("diagram", "The Context block labels its inputs u and v."),
        *[make_extracted_claim(f"call{i}", f"At step {i}, the result is D(z, u, v).") for i in range(5)],
        *claims(),
    ]
    c = checker(FakeAsyncHandler([]))
    c.max_pairs = 4
    rows, coverage = c.plan(items)
    assert len(rows) == 4
    assert coverage["relation_selected"] == 2
    assert coverage["relation_omitted_by_quota"] == 3
    assert any("relation_context" not in row for row in rows)


def test_different_values_reach_checker_and_cap_is_reported():
    c = checker(FakeAsyncHandler([]))
    rows, _ = c.plan(claims())
    assert len(rows) == 1
    many = [make_extracted_claim(str(i), f"The model achieves {i} percent accuracy on validation.") for i in range(10)]
    c.max_pairs = 2
    rows, coverage = c.plan(many)
    assert len(rows) == 2 and coverage["omitted_by_cap"] > 0


@pytest.mark.asyncio
async def test_alert_requires_two_sources_and_preserves_claims():
    h = FakeAsyncHandler([json.dumps([dict(pair_id="p0000", status="contradiction",
        issue_type="numerical", reason="Same validation result differs.", evidence_ids=["a#source0", "b#source0"],
        left_claim_quote="90 percent accuracy", right_claim_quote="95 percent accuracy")])])
    items = claims()
    before = [x.model_dump() for x in items]
    result = await checker(h).check(items)
    assert result["decisions"][0]["status"] == "contradiction"
    assert [x.model_dump() for x in items] == before


@pytest.mark.asyncio
async def test_unknown_evidence_does_not_become_a_clean_bill_of_health():
    h = FakeAsyncHandler([json.dumps([dict(pair_id="p0000", status="contradiction",
        issue_type="numerical", reason="Different.", evidence_ids=["fabricated"])])])
    result = await checker(h).check(claims())
    assert result["failed_batches"] and not result["decisions"]
    assert not result["complete_for_selected_pairs"]


@pytest.mark.asyncio
async def test_transport_failure_retains_unchecked_pair():
    result = await checker(FakeAsyncHandler([RuntimeError("unavailable")])).check(claims())
    assert len(result["candidate_pairs"]) == 1 and result["failed_batches"]


@pytest.mark.asyncio
async def test_source_only_quote_cannot_anchor_alert_to_claim():
    h = FakeAsyncHandler([json.dumps([dict(pair_id="p0000", status="contradiction",
        issue_type="numerical", reason="Different.", evidence_ids=["a#source0", "b#source0"],
        left_claim_quote="Accuracy was 90.", right_claim_quote="95 percent accuracy")])])
    result = await checker(h).check(claims())
    assert result["failed_batches"] and not result["decisions"]


@pytest.mark.asyncio
async def test_figure_context_is_scoped_cited_and_non_destructive():
    items = [make_extracted_claim("a", "Figure 4 compares the generated motions."),
             make_extracted_claim("b", "Figure 6 compares the generated motions.")]
    h = FakeAsyncHandler([json.dumps([dict(pair_id="p0000", status="potential_inconsistency",
        issue_type="reference_mismatch", reason="Figure 6 is not located by the scan.",
        evidence_ids=["a#source0", "b#source0", "inventory"],
        left_claim_quote="Figure 4", right_claim_quote="Figure 6")])])
    c = ContradictionChecker(ClaimExtractor(h, max_retries=1)._request_validated,
        figure_context=[dict(id="inventory", text="Captions 1–4; text-layer only"),
                        dict(id="f4", text="Motion comparison", figure_numbers=["4"]),
                        dict(id="f99", text="Other", figure_numbers=["99"])])
    before = [x.model_dump() for x in items]
    result = await c.check(items)
    assert {x["id"] for x in result["candidate_pairs"][0]["figure_context"]} == {"inventory", "f4"}
    assert result["decisions"][0]["issue_type"] == "reference_mismatch"
    assert [x.model_dump() for x in items] == before


@pytest.mark.asyncio
async def test_optional_stage_runs_after_dedup(monkeypatch):
    extractor = ClaimExtractor(FakeAsyncHandler([]), check_contradictions=True)
    original, surviving = claims(), claims()[:1]
    async def select(_): return ["s1"]
    async def extract(*_): return original
    async def dedup(_): return surviving, []
    async def check(self, received):
        assert received is surviving
        return {"decisions": [], "tested": True}
    monkeypatch.setattr(extractor, "_step_1_select_sections", select)
    monkeypatch.setattr(extractor, "_step_2_extract_claims", extract)
    monkeypatch.setattr(extractor, "_step_3_deduplicate_claims", dedup)
    monkeypatch.setattr(ContradictionChecker, "check", check)
    result = await extractor.extract([make_paper_section()])
    assert result.contradiction_analysis["tested"]
    assert "contradiction_analysis" in result.to_legacy_dict()


def test_link_projection_is_symmetric_and_drops_stale_partners():
    items = [make_extracted_claim(k, "An assertion.") for k in "abcd"]
    items[-1].contradiction = True
    items[-1].contradicts_claim_ids = ["deleted"]
    pairs = [("a", "c"), ("a", "b"), ("b", "a"), ("a", "d")]
    analysis = {
        "candidate_pairs": [{"pair_id": str(i), "left": {"claim_id": a}, "right": {"claim_id": b}}
                            for i, (a, b) in enumerate(pairs)],
        "decisions": [{"pair_id": str(i), "status": "contradiction" if i < 3 else "potential_inconsistency"}
                      for i in range(4)],
    }
    linked = attach_contradiction_links(items, analysis)
    assert [c.contradicts_claim_ids for c in linked] == [["b", "c"], ["a"], ["a"], []]
    assert all(c.contradiction for c in linked)
    assert attach_contradiction_links(linked, analysis) == linked
    assert items[0].contradicts_claim_ids == []


@pytest.mark.asyncio
async def test_links_reach_serialized_claims_and_resumed_reader(tmp_path, monkeypatch):
    from osa_tool.operations.analysis.paper_claims.models import ExtractedClaim

    decision = dict(pair_id="p0000", status="contradiction", issue_type="numerical",
                    reason="Same metric and conditions.", evidence_ids=["a#source0", "b#source0"],
                    left_claim_quote="90 percent", right_claim_quote="95 percent")
    extractor = ClaimExtractor(FakeAsyncHandler([json.dumps([decision])]), check_contradictions=True)
    from unittest.mock import AsyncMock
    monkeypatch.setattr(extractor, "_step_1_select_sections", AsyncMock(return_value=["s001"]))
    monkeypatch.setattr(extractor, "_step_2_extract_claims", AsyncMock(return_value=claims()))
    monkeypatch.setattr(extractor, "_step_3_deduplicate_claims", AsyncMock(return_value=(claims(), [])))
    result = await extractor.extract([make_paper_section()])
    for name, payload in [("typed", result.model_dump(mode="json")), ("legacy", result.to_legacy_dict())]:
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf8")
        rows = load_claims_json(path).claims
        assert [r["contradicts_claim_ids"] for r in rows] == [["b"], ["a"]]
        assert all(r["contradiction"] for r in rows)
    old = claims()[0].model_dump(exclude={"contradicts_claim_ids"})
    assert ExtractedClaim.model_validate(old).contradicts_claim_ids == []
