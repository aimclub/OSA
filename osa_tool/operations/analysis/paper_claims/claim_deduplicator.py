"""Fail-safe LLM-assisted claim deduplication."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Any

from pydantic import TypeAdapter
from rich.progress import track

from osa_tool.operations.analysis.paper_claims.claim_input_planner import ClaimInputPlanner
from osa_tool.operations.analysis.paper_claims.models import DedupSelection, ExtractedClaim
from osa_tool.utils.logger import logger
from osa_tool.utils.token_counter import count_tokens

ValidatedRequest = Callable[..., Awaitable[Any]]


class ClaimDeduplicator:
    """Deduplicate claims while preserving evidence when an LLM request fails."""

    def __init__(
        self,
        *,
        request_validated: ValidatedRequest,
        input_planner: ClaimInputPlanner,
        deduplication_system: str,
        dedup_batch_size: int,
    ) -> None:
        self._request_validated = request_validated
        self._input_planner = input_planner
        self._deduplication_system = deduplication_system
        self._dedup_batch_size = dedup_batch_size

    async def deduplicate(self, claims: list[ExtractedClaim]) -> tuple[list[ExtractedClaim], list[DedupSelection]]:
        """Deduplicate claims, retain contradictions, and enrich kept claims."""
        if not claims:
            logger.info("Claim extraction step 3/3 skipped: no claims to deduplicate")
            return [], []

        logger.info(
            "Claim extraction step 3/3: deduplicating %s claims with batch_size=%s",
            len(claims),
            self._dedup_batch_size,
        )
        batches = self._deduplication_batches(claims)
        filtered: list[ExtractedClaim] = []
        selections: list[DedupSelection] = []
        for batch_index, batch_claims in track(
            list(enumerate(batches, start=1)),
            description="Deduplicating claim batches",
        ):
            batch_filtered, batch_selections = await self._deduplicate_claim_batch(
                batch_claims,
                request_name=f"Claim deduplication batch {batch_index}/{len(batches)}",
            )
            filtered.extend(batch_filtered)
            selections.extend(batch_selections)

        if len(batches) > 1 and filtered:
            filtered, selections = await self._deduplicate_global_survivors(filtered)

        ratio = len(filtered) / len(claims)
        logger.info(
            "Claim extraction step 3/3 completed: retained %s/%s claims (%.1f%%)",
            len(filtered),
            len(claims),
            ratio * 100,
        )
        return filtered, selections

    @staticmethod
    def _deduplication_prompt(claims: list[ExtractedClaim]) -> str:
        dedup_input = [
            {
                "claim_id": claim.claim_id,
                "claim": claim.claim,
                "contradiction": claim.contradiction,
            }
            for claim in claims
        ]
        return (
            "Below is the JSON array of claims extracted from the report sections. Apply the deduplication and contradiction rules.\n"
            + json.dumps(dedup_input, ensure_ascii=False)
            + "\nReturn ONLY the final processed JSON array."
        )

    def _deduplication_batches(self, claims: list[ExtractedClaim]) -> list[list[ExtractedClaim]]:
        budget_info = self._input_planner.input_token_budget(self._deduplication_system)
        if budget_info is None:
            return [
                claims[index : index + self._dedup_batch_size]
                for index in range(0, len(claims), self._dedup_batch_size)
            ]

        user_budget, encoder = budget_info
        batches: list[list[ExtractedClaim]] = []
        current: list[ExtractedClaim] = []
        for claim in claims:
            candidate = [*current, claim]
            try:
                token_count = count_tokens(self._deduplication_prompt(candidate), encoder)
            except Exception as exc:
                logger.warning("Token counting failed; falling back to count-bounded deduplication batches: %s", exc)
                return [
                    claims[index : index + self._dedup_batch_size]
                    for index in range(0, len(claims), self._dedup_batch_size)
                ]

            if current and (len(candidate) > self._dedup_batch_size or token_count > user_budget):
                batches.append(current)
                current = [claim]
                try:
                    single_token_count = count_tokens(self._deduplication_prompt(current), encoder)
                except Exception as exc:
                    logger.warning(
                        "Token counting failed; falling back to count-bounded deduplication batches: %s",
                        exc,
                    )
                    return [
                        claims[index : index + self._dedup_batch_size]
                        for index in range(0, len(claims), self._dedup_batch_size)
                    ]
                if single_token_count > user_budget:
                    logger.warning(
                        "Single claim %s exceeds deduplication input budget; sending it unchanged",
                        claim.claim_id,
                    )
            else:
                current = candidate

        if current:
            batches.append(current)
        if len(batches) > 1:
            logger.info(
                "Claim extraction step 3/3: split deduplication into %s token-bounded batches",
                len(batches),
            )
        return batches

    def _deduplication_prompt_fits(self, claims: list[ExtractedClaim]) -> bool:
        if len(claims) > self._dedup_batch_size:
            return False
        budget_info = self._input_planner.input_token_budget(self._deduplication_system)
        if budget_info is None:
            return True
        user_budget, encoder = budget_info
        try:
            return count_tokens(self._deduplication_prompt(claims), encoder) <= user_budget
        except Exception as exc:
            logger.warning("Token counting failed; assuming deduplication prompt fits current budget: %s", exc)
            return True

    async def _deduplicate_global_survivors(
        self, claims: list[ExtractedClaim]
    ) -> tuple[list[ExtractedClaim], list[DedupSelection]]:
        """Compare survivors across batch boundaries without exceeding the dedup batch size."""
        if len(claims) <= self._dedup_batch_size:
            logger.info(
                "Claim extraction step 3/3: running final deduplication pass over %s batch survivors",
                len(claims),
            )
            return await self._deduplicate_claim_group(claims, request_name="Claim deduplication final pass")

        chunk_size = max(1, self._dedup_batch_size // 2)
        chunks = [claims[index : index + chunk_size] for index in range(0, len(claims), chunk_size)]
        total_groups = len(chunks) * (len(chunks) + 1) // 2
        active = {claim.claim_id: claim for claim in claims}
        original_order = {claim.claim_id: index for index, claim in enumerate(claims)}
        logger.info(
            "Claim extraction step 3/3: running global pairwise deduplication over %s survivors "
            "using %s groups of up to %s claims",
            len(claims),
            total_groups,
            self._dedup_batch_size,
        )

        group_number = 0
        for left_index, left_chunk in enumerate(chunks):
            for right_index in range(left_index, len(chunks)):
                group_number += 1
                group_ids = [claim.claim_id for claim in left_chunk]
                if right_index != left_index:
                    group_ids.extend(claim.claim_id for claim in chunks[right_index])
                group = [active[claim_id] for claim_id in group_ids if claim_id in active]
                if len(group) <= 1:
                    continue

                kept, _chosen = await self._deduplicate_claim_group(
                    group,
                    request_name=f"Claim deduplication global group {group_number}/{total_groups}",
                )
                self._apply_dedup_result(active, group, kept)

        filtered = sorted(active.values(), key=lambda claim: original_order[claim.claim_id])
        return filtered, self._dedup_selections(filtered)

    async def _deduplicate_claim_group(
        self,
        claims: list[ExtractedClaim],
        *,
        request_name: str,
    ) -> tuple[list[ExtractedClaim], list[DedupSelection]]:
        """Deduplicate a group without sending prompts over token or count limits."""
        batches = self._deduplication_batches(claims)
        if len(batches) == 1:
            return await self._deduplicate_claim_batch(batches[0], request_name=request_name)

        logger.info("%s split into %s token-bounded sub-batches", request_name, len(batches))
        survivor_batches: list[list[ExtractedClaim]] = []
        for batch_index, batch_claims in enumerate(batches, start=1):
            batch_filtered, _batch_selections = await self._deduplicate_claim_batch(
                batch_claims,
                request_name=f"{request_name} sub-batch {batch_index}/{len(batches)}",
            )
            survivor_batches.append(batch_filtered)
        return await self._deduplicate_cross_sub_batch_survivors(survivor_batches, request_name=request_name)

    @staticmethod
    def _apply_dedup_result(
        active: dict[str, ExtractedClaim],
        group: list[ExtractedClaim],
        kept: list[ExtractedClaim],
    ) -> None:
        kept_by_id = {claim.claim_id: claim for claim in kept}
        for claim_id, kept_claim in kept_by_id.items():
            current = active.get(claim_id)
            if current is None:
                continue
            active[claim_id] = kept_claim.model_copy(
                update={"contradiction": current.contradiction or kept_claim.contradiction}
            )
        for claim in group:
            if claim.claim_id not in kept_by_id:
                active.pop(claim.claim_id, None)

    async def _deduplicate_cross_sub_batch_survivors(
        self,
        survivor_batches: list[list[ExtractedClaim]],
        *,
        request_name: str,
    ) -> tuple[list[ExtractedClaim], list[DedupSelection]]:
        survivors = [claim for batch in survivor_batches for claim in batch]
        if len(survivors) <= 1:
            return survivors, self._dedup_selections(survivors)

        active = {claim.claim_id: claim for claim in survivors}
        original_order = {claim.claim_id: index for index, claim in enumerate(survivors)}
        total_pairs = len(survivor_batches) * (len(survivor_batches) - 1) // 2
        pair_number = 0
        for left_index, left_batch in enumerate(survivor_batches):
            for right_index in range(left_index + 1, len(survivor_batches)):
                pair_number += 1
                right_batch = survivor_batches[right_index]
                group_ids = [claim.claim_id for claim in [*left_batch, *right_batch]]
                group = [active[claim_id] for claim_id in group_ids if claim_id in active]
                if len(group) <= 1:
                    continue
                if self._deduplication_prompt_fits(group):
                    kept, _chosen = await self._deduplicate_claim_batch(
                        group,
                        request_name=f"{request_name} cross-sub-batch group {pair_number}/{total_pairs}",
                    )
                    self._apply_dedup_result(active, group, kept)
                    continue

                comparison_number = 0
                for left_claim in left_batch:
                    for right_claim in right_batch:
                        left_active = active.get(left_claim.claim_id)
                        right_active = active.get(right_claim.claim_id)
                        if left_active is None or right_active is None:
                            continue
                        comparison_number += 1
                        pair = [left_active, right_active]
                        if not self._deduplication_prompt_fits(pair):
                            logger.warning(
                                "%s: cannot compare verbose claims %s and %s within deduplication input budget",
                                request_name,
                                left_active.claim_id,
                                right_active.claim_id,
                            )
                            continue
                        kept, _chosen = await self._deduplicate_claim_batch(
                            pair,
                            request_name=(
                                f"{request_name} cross-sub-batch pair {pair_number}/{total_pairs}."
                                f"{comparison_number}"
                            ),
                        )
                        self._apply_dedup_result(active, pair, kept)

        filtered = sorted(active.values(), key=lambda claim: original_order[claim.claim_id])
        return filtered, self._dedup_selections(filtered)

    async def _deduplicate_claim_batch(
        self,
        claims: list[ExtractedClaim],
        *,
        request_name: str,
    ) -> tuple[list[ExtractedClaim], list[DedupSelection]]:
        """Deduplicate one bounded batch and preserve all claims on LLM failure."""
        claims_by_id = {claim.claim_id: claim for claim in claims}

        def validate_dedup(items: list[DedupSelection]) -> None:
            if claims and not items:
                raise ValueError(f"Deduplication returned 0 claims for non-empty input of {len(claims)} claims")
            ids = [item.claim_id for item in items]
            if len(ids) != len(set(ids)) or any(item not in claims_by_id for item in ids):
                raise ValueError("Deduplication contains duplicate or unknown claim IDs")
            rewritten = [item.claim_id for item in items if item.claim != claims_by_id[item.claim_id].claim]
            if rewritten:
                raise ValueError(
                    "Deduplication must copy claim text verbatim; rewritten claim IDs: " + ", ".join(rewritten)
                )

        try:
            selections = await self._request_validated(
                self._deduplication_prompt(claims),
                self._deduplication_system,
                TypeAdapter(list[DedupSelection]),
                validate_dedup,
                request_name=request_name,
            )
        except Exception as exc:
            return self._fallback_deduplication(claims, request_name=request_name, reason=str(exc))

        contradictory_texts = {claim.claim for claim in claims if claim.contradiction}
        replacement_ids = {selection.claim_id for selection in selections if selection.claim in contradictory_texts}
        if contradictory_texts and not replacement_ids:
            logger.debug(
                "%s: no exact replacement mapping for an existing contradiction; using the current deduplication "
                "response flags",
                request_name,
            )
        if replacement_ids:
            selections = [
                selection.model_copy(
                    update={"contradiction": selection.contradiction or selection.claim_id in replacement_ids}
                )
                for selection in selections
            ]

        selection_by_id = {item.claim_id: item for item in selections}
        filtered = [
            claim.model_copy(
                update={"contradiction": claim.contradiction or selection_by_id[claim.claim_id].contradiction}
            )
            for claim in claims
            if claim.claim_id in selection_by_id
        ]
        ratio = len(filtered) / len(claims)
        logger.info(
            "%s completed: retained %s/%s claims (%.1f%%)",
            request_name,
            len(filtered),
            len(claims),
            ratio * 100,
        )
        return filtered, selections

    @staticmethod
    def _dedup_selections(claims: list[ExtractedClaim]) -> list[DedupSelection]:
        return [
            DedupSelection(
                claim_id=claim.claim_id,
                claim=claim.claim,
                contradiction=claim.contradiction,
            )
            for claim in claims
        ]

    def _fallback_deduplication(
        self,
        claims: list[ExtractedClaim],
        *,
        request_name: str,
        reason: str,
    ) -> tuple[list[ExtractedClaim], list[DedupSelection]]:
        logger.warning(
            "%s failed after retries; preserving %s original claims without LLM deduplication. reason=%s",
            request_name,
            len(claims),
            reason,
        )
        return list(claims), self._dedup_selections(claims)
