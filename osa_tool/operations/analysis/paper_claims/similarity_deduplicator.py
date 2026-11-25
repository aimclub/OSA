"""Conservative, auditable deduplication with bounded lexical candidate retrieval."""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from itertools import combinations
from typing import Any, Literal

from pydantic import Field, TypeAdapter

from osa_tool.operations.analysis.paper_claims.claim_deduplicator import ClaimDeduplicator
from osa_tool.operations.analysis.paper_claims.models import ClaimSource, DedupSelection, ExtractedClaim, StrictModel
from osa_tool.utils.token_counter import count_tokens


class PairDecision(StrictModel):
    pair_id: str
    relation: Literal["duplicate", "contradiction", "distinct", "uncertain"]


class MergeReview(StrictModel):
    pair_id: str
    retain: Literal["left", "right", "either", "neither"]
    reason: str


class RemovalCheck(StrictModel):
    preserved: bool
    reason: str = Field(min_length=1)


class SimilarityClaimDeduplicator(ClaimDeduplicator):
    """Exact text grouping, TF-IDF top-k candidates, then explicit LLM pair decisions.

    This retrieves potential duplicates, not an exhaustive set of contradictions.
    Unknown pair relations never justify transitive merging.
    """

    similarity_threshold = 0.55
    identifier_similarity_threshold = 0.40
    shared_identifiers_min = 2
    neighbors_per_claim = 4
    pairs_per_request = 24
    evidence_chars = 800
    stopwords = frozenset(
        "a an the is are was were be been being of to in on at for from by with and or that this these those it its as uses used using use".split()
    )

    @staticmethod
    def exact_key(text: str) -> str:
        # Whitespace inside quoted code/formulas can be meaningful too.
        return text

    @staticmethod
    def assertion_scope(claim: ExtractedClaim) -> tuple[str, ...]:
        """Explicit source identity/metric/conditions, separate from quotations.

        The optional assertion_scope is supplied by a structured importer. It
        must not contain the measured value: unequal values are already guarded
        by the claim-text comparison. Differing declared scopes cannot be
        collapsed just because an underspecified sentence is identical.
        """
        return tuple(
            sorted(
                {
                    json.dumps(source.metadata["assertion_scope"], sort_keys=True, ensure_ascii=False)
                    for source in claim.sources
                    if source.metadata.get("assertion_scope")
                }
            )
        )

    @classmethod
    def scope_collision(cls, left: ExtractedClaim, right: ExtractedClaim) -> bool:
        return (
            left.claim == right.claim
            and cls.assertion_scope(left) != cls.assertion_scope(right)
            and bool(cls.assertion_scope(left) or cls.assertion_scope(right))
        )

    @staticmethod
    def incompatible(left: str, right: str) -> bool:
        def numbers(s: str) -> Counter:
            return Counter(re.findall(r"(?<!\w)[+−-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?", s))

        def negation(s: str) -> Counter:
            return Counter(re.findall(r"\b(?:not|no|never|without|neither|не|нет|без)\b|n't\b", s.lower()))

        def qualifications(s: str) -> set[str]:
            return set(
                re.findall(
                    r"\b(?:may|might|can|could|must|should|hypoth\w*|real-world|synthetic|simulated|"
                    r"supervised|unsupervised|pretrained|only|all|each|every|most|some|many|often|generally|typically)\b",
                    s.lower(),
                )
            )

        def names(s: str) -> set[str]:
            # A conservative surface-form gate, not a named-entity recognizer. Unknown aliases
            # remain separate; context-based entity resolution belongs in another stage.
            generic = {t.title() for t in SimilarityClaimDeduplicator.stopwords} | {
                "Both",
                "Our",
                "We",
                "Random",
                "Best",
                "First",
                "Second",
                "During",
                "Model",
                "Method",
                "Figure",
                "Table",
                "Algorithm",
                "Equation",
                "Appendix",
                "Step",
                "All",
                "Each",
            }
            return set(re.findall(r"\b[A-Z][A-Za-z0-9_]*\b", s)) - generic

        return (
            numbers(left) != numbers(right)
            or negation(left) != negation(right)
            or qualifications(left) != qualifications(right)
            or names(left) != names(right)
        )

    @staticmethod
    def with_sources(claim: ExtractedClaim) -> ExtractedClaim:
        if claim.sources:
            return claim.model_copy(deep=True)
        source = ClaimSource(
            claim_id=claim.claim_id,
            claim=claim.claim,
            original_text=claim.original_text,
            section_id=claim.section_id,
            section_name=claim.section_name,
            section_heading_raw=claim.section_heading_raw,
            metadata={
                "category": claim.category.value,
                "value": claim.value,
                "verifiability": claim.verifiability.value,
                "contradiction": claim.contradiction,
            },
        )
        return claim.model_copy(update={"sources": [source]})

    @staticmethod
    def merge(left: ExtractedClaim, right: ExtractedClaim) -> ExtractedClaim:
        sources = {s.claim_id: s for s in left.sources}
        for source in right.sources:
            if source.claim_id in sources and sources[source.claim_id] != source:
                raise ValueError(f"Conflicting provenance for source {source.claim_id}")
            sources[source.claim_id] = source
        # A warning shared by the two merged endpoints no longer identifies a distinct pair.
        collapsed = set(left.potential_inconsistency_pair_ids) & set(right.potential_inconsistency_pair_ids)
        warnings = dict.fromkeys(left.potential_inconsistency_pair_ids + right.potential_inconsistency_pair_ids)
        comments = {c.pair_id: c for c in right.review_comments}
        comments.update({c.pair_id: c for c in left.review_comments})
        return left.model_copy(update={
            "sources": list(sources.values()),
            "contradiction": left.contradiction or right.contradiction,
            "potential_inconsistency_pair_ids": [key for key in warnings if key not in collapsed],
            "review_comments": [v for k, v in comments.items() if k not in collapsed],
        })

    def candidate_pairs(self, claims: list[ExtractedClaim]) -> list[tuple[int, int, float]]:
        bags = [Counter(t for t in re.findall(r"\w+", c.claim.lower()) if t not in self.stopwords) for c in claims]
        # Shared snake_case code symbols can anchor paraphrases despite different prose.
        # This only broadens retrieval; all safety gates and LLM decisions still apply.
        identifiers = [{t for t in bag if "_" in t and not t.startswith("_") and not t.endswith("_")} for bag in bags]
        df = Counter(t for bag in bags for t in bag)
        vectors = []
        for bag in bags:
            weights = {t: (1 + math.log(n)) * (1 + math.log((1 + len(claims)) / (1 + df[t]))) for t, n in bag.items()}
            norm = math.sqrt(sum(v * v for v in weights.values())) or 1
            vectors.append({t: v / norm for t, v in weights.items()})
        inverted = defaultdict(list)
        for i, vec in enumerate(vectors):
            for token, weight in vec.items():
                inverted[token].append((i, weight))
        scores = defaultdict(float)
        for entries in inverted.values():
            for (i, a), (j, b) in combinations(entries, 2):
                scores[i, j] += a * b
        nearest = defaultdict(list)
        for (i, j), score in scores.items():
            identifier_match = (
                score >= self.identifier_similarity_threshold
                and len(identifiers[i] & identifiers[j]) >= self.shared_identifiers_min
            )
            if self.scope_collision(claims[i], claims[j]):
                continue
            if (score < self.similarity_threshold and not identifier_match) or self.incompatible(
                claims[i].claim, claims[j].claim
            ):
                continue
            nearest[i].append((score, j))
            nearest[j].append((score, i))
        selected = set()
        for i, candidates in nearest.items():
            for _, j in sorted(candidates, key=lambda x: (-x[0], x[1]))[: self.neighbors_per_claim]:
                selected.add(tuple(sorted((i, j))))
        return [(i, j, scores[i, j]) for i, j in sorted(selected)]

    def pair_item(self, pair_id: str, left: ExtractedClaim, right: ExtractedClaim) -> dict[str, Any]:
        def item(claim: ExtractedClaim) -> dict[str, Any]:
            from .scope_context import review_packet

            return {
                **review_packet(claim),
                "section": claim.section_name,
                "evidence_excerpt": claim.original_text[: self.evidence_chars],
                "evidence_truncated": len(claim.original_text) > self.evidence_chars,
            }

        return {"pair_id": pair_id, "left": item(left), "right": item(right)}

    @staticmethod
    def pair_prompt(items: list[dict]) -> str:
        return json.dumps({"pairs": items}, ensure_ascii=False)

    def pair_batches(self, items: list[dict]) -> list[list[dict]]:
        budget = self._input_planner.input_token_budget(self._deduplication_system)
        settings = self._input_planner._settings()
        if budget is None and hasattr(settings, "context_window") and hasattr(settings, "max_tokens"):
            self.audit["oversized_pairs"].extend(item["pair_id"] for item in items)
            return []
        batches, current = [], []
        for item in items:
            proposed = [*current, item]
            fits = budget is None or count_tokens(self.pair_prompt(proposed), budget[1]) <= budget[0]
            if current and (len(proposed) > min(self.pairs_per_request, self._dedup_batch_size) or not fits):
                batches.append(current)
                current = []
            if budget and count_tokens(self.pair_prompt([item]), budget[1]) > budget[0]:
                self.audit["oversized_pairs"].append(item["pair_id"])
                continue
            current.append(item)
        if current:
            batches.append(current)
        return batches

    async def deduplicate(self, claims: list[ExtractedClaim]) -> tuple[list[ExtractedClaim], list[DedupSelection]]:
        if len({c.claim_id for c in claims}) != len(claims):
            raise ValueError("Claim IDs must be unique")
        self.audit = {
            "exact_merges": [],
            "candidate_pairs": [],
            "decisions": [],
            "semantic_merges": [],
            "merge_reviews": [],
            "removal_checks": [],
            "failed_batches": [],
            "oversized_pairs": [],
            "skipped_transitive_merges": [],
            "protected_merge_rejections": [],
        }
        grouped = {}
        seen_sources = set()
        for original in claims:
            claim = self.with_sources(original)
            for source in claim.sources:
                if source.claim_id in seen_sources:
                    raise ValueError(f"Source claim IDs must be unique across input records: {source.claim_id}")
                seen_sources.add(source.claim_id)
            key = (
                self.exact_key(claim.claim),
                self.assertion_scope(claim),
                claim.claim_id if claim.contradicts_claim_ids else None,
            )
            if key in grouped:
                self.audit["exact_merges"].append({"removed_id": claim.claim_id, "retained_id": grouped[key].claim_id})
                grouped[key] = self.merge(grouped[key], claim)
            else:
                grouped[key] = claim
        unique = list(grouped.values())
        pairs = self.candidate_pairs(unique)
        items = []
        lookup = {}
        for n, (i, j, score) in enumerate(pairs):
            pid = f"p{n:06}"
            lookup[pid] = (i, j)
            items.append(self.pair_item(pid, unique[i], unique[j]))
            self.audit["candidate_pairs"].append(
                {"pair_id": pid, "left_id": unique[i].claim_id, "right_id": unique[j].claim_id, "similarity": score}
            )
        relations = {}
        can_represent = set()
        for n, batch in enumerate(self.pair_batches(items), 1):
            expected = {p["pair_id"] for p in batch}

            def validate(decisions: list[PairDecision]) -> None:
                ids = [d.pair_id for d in decisions]
                if len(ids) != len(set(ids)) or set(ids) != expected:
                    raise ValueError("Return exactly one decision for every requested pair ID")

            try:
                decisions = await self._request_validated(
                    self.pair_prompt(batch),
                    self._deduplication_system,
                    TypeAdapter(list[PairDecision]),
                    validate,
                    request_name=f"Similar claim pairs batch {n}",
                )
            except Exception as exc:
                self.audit["failed_batches"].append({"batch": n, "pair_ids": sorted(expected), "error": str(exc)})
                continue
            duplicates = {d.pair_id for d in decisions if d.relation == "duplicate"}
            permitted = set()
            if duplicates:
                review_input = [p for p in batch if p["pair_id"] in duplicates]

                def validate_reviews(reviews):
                    if (
                        len(reviews) != len(duplicates)
                        or {r.pair_id for r in reviews} != duplicates
                        or any(not r.reason.strip() for r in reviews)
                    ):
                        raise ValueError("Each proposed removal needs a reasoned equivalence review")

                try:
                    reviews = await self._request_validated(
                        self.pair_prompt(review_input),
                        "Choose a representative only for two accounts of the same fact under the same conditions. "
                        "Check each direction separately. Return retain=left if the left text preserves everything "
                        "the right asserts, right for the reverse, either if both do, or neither. Preserve all "
                        "material qualifiers, direction, quantities and attribution. A more detailed description "
                        "can retain a shorter restatement. Different experimental scopes, distinct facts, or an "
                        "unresolved conflict require neither. Source excerpts clarify referents but cannot replace "
                        "a missing fact in the representative. Return an array with pair_id, retain, reason.",
                        TypeAdapter(list[MergeReview]),
                        validate_reviews,
                        request_name=f"Semantic merge review {n}",
                    )
                    permitted = {r.pair_id for r in reviews if r.retain != "neither"}
                    for review in reviews:
                        i, j = lookup[review.pair_id]
                        if review.retain in ("left", "either"):
                            can_represent.add((i, j))
                        if review.retain in ("right", "either"):
                            can_represent.add((j, i))
                    self.audit["merge_reviews"].extend(r.model_dump() for r in reviews)
                except Exception as exc:
                    self.audit["failed_batches"].append({"batch": n, "pair_ids": sorted(duplicates), "error": str(exc)})
            for decision in decisions:
                relation = decision.relation
                if relation == "duplicate" and decision.pair_id not in permitted:
                    relation = "uncertain"
                relations[lookup[decision.pair_id]] = relation
                self.audit["decisions"].append(decision.model_dump())
        active = {i: c for i, c in enumerate(unique)}
        groups = {i: {i} for i in active}
        owner = {i: i for i in active}
        # Set all flags before merging, so a duplicate representative inherits them.
        for (i, j), relation in sorted(relations.items()):
            if relation == "contradiction":
                for k in (i, j):
                    active[k] = active[k].model_copy(update={"contradiction": True})
        for (i, j), relation in sorted(relations.items()):
            if relation != "duplicate":
                continue
            left, right = sorted((owner[i], owner[j]))
            if left == right:
                continue
            if active[left].contradiction or active[right].contradiction:
                self.audit["protected_merge_rejections"].append([active[left].claim_id, active[right].claim_id])
                continue
            if any(
                self.incompatible(unique[a].claim, unique[b].claim) or self.scope_collision(unique[a], unique[b])
                for a in groups[left]
                for b in groups[right]
            ):
                self.audit["protected_merge_rejections"].append([unique[i].claim_id, unique[j].claim_id])
                continue
            # Complete-link: every cross-pair must independently be a confirmed duplicate.
            if not all(
                relations.get(tuple(sorted((a, b)))) == "duplicate" for a in groups[left] for b in groups[right]
            ):
                self.audit["skipped_transitive_merges"].append([unique[i].claim_id, unique[j].claim_id])
                continue
            if not all((left, member) in can_represent for member in groups[right]):
                if not all((right, member) in can_represent for member in groups[left]):
                    self.audit["protected_merge_rejections"].append([active[left].claim_id, active[right].claim_id])
                    continue
                left, right = right, left
            removal = {"removed": active[right].claim, "retained": active[left].claim}

            def validate_check(items):
                if len(items) != 1:
                    raise ValueError("Expected one removal check")

            try:
                (check,) = await self._request_validated(
                    json.dumps(removal, ensure_ascii=False),
                    "Read the retained text as a standalone assertion. Identify any information that a reader "
                    "would lose by deleting the removed text. Check the actor, action, relation, scope, qualifiers "
                    "and outcome. When the retained text alone "
                    "fully conveys the removed assertion, mark preserved true. Otherwise keep the original. "
                    "Return a one-item JSON array with preserved (boolean) and a specific reason.",
                    TypeAdapter(list[RemovalCheck]),
                    validate_check,
                    request_name="Check retained assertion",
                )
            except Exception as exc:
                self.audit["failed_batches"].append(
                    {"claim_ids": [active[left].claim_id, active[right].claim_id], "error": str(exc)}
                )
                continue
            self.audit["removal_checks"].append(
                {"removed_id": active[right].claim_id, "retained_id": active[left].claim_id, **check.model_dump()}
            )
            if not check.preserved:
                continue
            self.audit["semantic_merges"].append(
                {"removed_id": active[right].claim_id, "retained_id": active[left].claim_id}
            )
            active[left] = self.merge(active[left], active.pop(right))
            for member in groups.pop(right):
                groups[left].add(member)
                owner[member] = left
        kept = [active[i] for i in sorted(active)]
        self.audit["source_to_representative"] = {s.claim_id: c.claim_id for c in kept for s in c.sources}
        return kept, self._dedup_selections(kept)
