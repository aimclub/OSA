import json
from types import SimpleNamespace

import pytest

from osa_tool.operations.analysis.paper_claims.claim_deduplicator import ClaimDeduplicator
from osa_tool.operations.analysis.paper_claims.claim_extractor import ClaimExtractor
from osa_tool.utils.prompts_builder import PromptLoader
from tests.unit.operations.analysis.paper_claims.fixtures import (
    FakeAsyncHandler as FakeHandler,
    make_extracted_claim as extracted_claim,
    word_token_count as fake_token_count,
)


def deduplicator(handler, *, dedup_batch_size=100) -> ClaimDeduplicator:
    return ClaimExtractor(handler, dedup_batch_size=dedup_batch_size)._deduplicator


@pytest.mark.asyncio
async def test_deduplication_transfers_existing_contradiction_to_replacement_representative():
    claims = [
        extracted_claim("c0001", "The model uses configuration A.").model_copy(update={"contradiction": True}),
        extracted_claim("c0002", "The model uses configuration A."),
        extracted_claim("c0003", "The model uses configuration B."),
    ]
    handler = FakeHandler(
        [
            json.dumps(
                [
                    {"claim_id": "c0002", "claim": claims[1].claim, "contradiction": False},
                    {"claim_id": "c0003", "claim": claims[2].claim, "contradiction": False},
                ],
                ensure_ascii=False,
            )
        ]
    )

    filtered, selections = await deduplicator(handler)._deduplicate_claim_batch(
        claims,
        request_name="Test deduplication",
    )

    assert [claim.claim_id for claim in filtered] == ["c0002", "c0003"]
    assert filtered[0].contradiction is True
    assert filtered[1].contradiction is False
    assert selections[0].contradiction is True
    assert selections[1].contradiction is False


def test_deduplication_batches_respect_model_input_token_budget(monkeypatch):
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_claims.claim_deduplicator.count_tokens",
        fake_token_count,
    )
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_claims.claim_input_planner.count_tokens",
        fake_token_count,
    )
    system = PromptLoader().get("paper_claims.deduplication_system")
    max_tokens = 80
    user_budget = 130
    handler = FakeHandler([])
    handler.model_settings = SimpleNamespace(
        context_window=fake_token_count(system) + max_tokens + 256 + user_budget,
        max_tokens=max_tokens,
        encoder="fake",
    )
    subject = deduplicator(handler)
    claims = [extracted_claim(f"c{index:04d}", "Claim " + "token " * 30) for index in range(1, 6)]

    batches = subject._deduplication_batches(claims)

    assert len(batches) > 1
    assert [claim.claim_id for batch in batches for claim in batch] == [claim.claim_id for claim in claims]
    assert all(fake_token_count(subject._deduplication_prompt(batch)) <= user_budget for batch in batches)


@pytest.mark.asyncio
async def test_deduplicate_claim_group_compares_survivors_across_token_split_sub_batches(monkeypatch):
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_claims.claim_deduplicator.count_tokens",
        fake_token_count,
    )
    monkeypatch.setattr(
        "osa_tool.operations.analysis.paper_claims.claim_input_planner.count_tokens",
        fake_token_count,
    )
    system = PromptLoader().get("paper_claims.deduplication_system")
    max_tokens = 80
    user_budget = 130
    claims = [
        extracted_claim("c0001", "Unique claim " + "token " * 30),
        extracted_claim("c0002", "Duplicate verbose claim " + "token " * 30),
        extracted_claim("c0003", "Duplicate verbose claim " + "token " * 30),
    ]
    handler = FakeHandler(
        [
            json.dumps(
                [
                    {"claim_id": "c0001", "claim": claims[0].claim, "contradiction": False},
                    {"claim_id": "c0002", "claim": claims[1].claim, "contradiction": False},
                ]
            ),
            json.dumps([{"claim_id": "c0003", "claim": claims[2].claim, "contradiction": False}]),
            json.dumps(
                [
                    {"claim_id": "c0001", "claim": claims[0].claim, "contradiction": False},
                    {"claim_id": "c0003", "claim": claims[2].claim, "contradiction": False},
                ]
            ),
            json.dumps([{"claim_id": "c0002", "claim": claims[1].claim, "contradiction": False}]),
        ]
    )
    handler.model_settings = SimpleNamespace(
        context_window=fake_token_count(system) + max_tokens + 256 + user_budget,
        max_tokens=max_tokens,
        encoder="fake",
    )

    filtered, selections = await deduplicator(handler)._deduplicate_claim_group(
        claims,
        request_name="Test deduplication group",
    )

    assert [claim.claim_id for claim in filtered] == ["c0001", "c0002"]
    assert [selection.claim_id for selection in selections] == ["c0001", "c0002"]
    assert len(handler.prompts) == 4
    assert '"claim_id": "c0002"' in handler.prompts[-1]
    assert '"claim_id": "c0003"' in handler.prompts[-1]
