import json

import pytest

from osa_tool.operations.analysis.paper_claims.contradiction_checker import attach_contradiction_links
from osa_tool.operations.analysis.paper_claims.cross_section_pairs import augment, propose, remove_resolved
from tests.unit.operations.analysis.paper_claims.fixtures import make_extracted_claim


@pytest.mark.asyncio
async def test_duplicate_nominations_create_one_reciprocal_flag_without_changing_claim_text():
    claims = [
        make_extracted_claim("a", "Validation accuracy is 90%.", original_text="Validation accuracy is 90%."),
        make_extracted_claim("b", "Validation accuracy is 92%.", original_text="Validation accuracy is 92%."),
    ]
    before = [c.model_dump() for c in claims]

    async def request(prompt, system, adapter, validate, *, request_name):
        if request_name.startswith("Paper-wide"):
            values = [{"left": 1, "right": 0, "question": "Do the two reported validation scores agree?"}]
        elif request_name.startswith("Consistency"):
            p = json.loads(prompt)[0]
            values = [{"pair_id": p["pair_id"], "status": "contradiction", "issue_type": "numerical",
                       "finding_kind": "direct_conflict", "finding_support": "fully_supported",
                       "reason": "The same validation score differs.", "evidence_ids": ["a#source0", "b#source0"],
                       "left_claim_quote": "90%", "right_claim_quote": "92%"}]
        else:
            values = []
        rows = adapter.validate_python(values)
        validate(rows)
        return rows

    pairs, failures = await propose(claims, request)
    assert len(pairs) == 1 and not failures
    analysis = {"candidate_pairs": [], "decisions": [], "coverage": {}, "failed_batches": []}
    analysis = await augment(analysis, pairs, failures, request)
    await remove_resolved(analysis, request)
    flagged = attach_contradiction_links(claims, analysis)
    assert [c.contradicts_claim_ids for c in flagged] == [["b"], ["a"]]
    assert [c.claim for c in flagged] == [c.claim for c in claims]
    assert [c.model_dump() for c in claims] == before


@pytest.mark.asyncio
async def test_failed_counterevidence_request_keeps_existing_decision():
    decision = {"pair_id": "p", "reason": "Possibly different scope.", "status": "potential_inconsistency",
                "finding_support": "partially_supported"}
    side = {"claim_id": "a", "claim": "A", "evidence": [{"id": "a#source0", "text": "A"}]}
    analysis = {"candidate_pairs": [{"pair_id": "p", "left": side, "right": dict(side, claim_id="b")}],
                "decisions": [decision]}

    async def unavailable(*args, **kwargs):
        raise TimeoutError("model unavailable")

    await remove_resolved(analysis, unavailable)
    assert analysis["decisions"] == [decision]
    assert analysis["counterevidence_review"]["failed_batches"][0]["pair_ids"] == ["p"]
