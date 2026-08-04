"""Prompt-safe input construction for the paper-claim extraction stages."""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from osa_tool.operations.analysis.paper_claims.models import PaperSection
from osa_tool.utils.logger import logger
from osa_tool.utils.token_counter import _get_encoder, count_tokens


@dataclass(frozen=True)
class SectionSelectionBatch:
    """A bounded selection request and its hierarchy-only context."""

    context_sections: list[PaperSection]
    candidate_sections: list[PaperSection]


class ClaimInputPlanner:
    """Build context-bounded prompts without making LLM requests."""

    def __init__(self, model_settings: Any | Callable[[], Any | None] | None) -> None:
        self._model_settings = model_settings if callable(model_settings) else lambda: model_settings

    def _settings(self) -> Any | None:
        return self._model_settings()

    def repair_reserve_tokens(self) -> int:
        settings = self._settings()
        if settings is None or not hasattr(settings, "context_window") or not hasattr(settings, "max_tokens"):
            return 0
        context_window = getattr(settings, "context_window", 0)
        base_input_budget = context_window - getattr(settings, "max_tokens", 0) - 256
        configured_reserve = min(2048, max(512, context_window // 10))
        return max(0, min(configured_reserve, base_input_budget - 1))

    def input_token_budget(self, system: str) -> tuple[int, str] | None:
        settings = self._settings()
        if settings is None or not hasattr(settings, "context_window") or not hasattr(settings, "max_tokens"):
            return None
        encoder = getattr(settings, "encoder", "cl100k_base")
        total_input_budget = getattr(settings, "context_window", 0) - getattr(settings, "max_tokens", 0) - 256
        if total_input_budget <= 0:
            return None
        try:
            system_tokens = count_tokens(system, encoder)
        except Exception as exc:
            logger.warning("Token encoder unavailable; token-aware batching disabled: %s", exc)
            return None
        budget = total_input_budget - system_tokens
        if budget <= 0:
            return None
        return budget, encoder

    @staticmethod
    def _section_option(section: PaperSection) -> dict[str, Any]:
        return {
            "section_id": section.section_id,
            "name": section.name,
            "heading_meta": section.heading_meta.model_dump(mode="json"),
        }

    @staticmethod
    def _numbering_prefixes(numbering: str | None) -> list[str]:
        if not numbering:
            return []
        normalized = numbering.strip().strip(".")
        if not normalized:
            return []
        parts = [part for part in normalized.split(".") if part]
        return [".".join(parts[:index]) for index in range(1, len(parts))]

    @classmethod
    def section_ancestors(cls, sections: list[PaperSection]) -> dict[str, list[PaperSection]]:
        """Resolve heading ancestors, including flattened numbered headings."""
        ancestors: dict[str, list[PaperSection]] = {}
        stack: list[PaperSection] = []
        numbered_sections: dict[str, PaperSection] = {}
        order_by_id: dict[str, int] = {}
        for index, section in enumerate(sections):
            order_by_id[section.section_id] = index
            while stack and stack[-1].heading_meta.level >= section.heading_meta.level:
                stack.pop()
            combined = {ancestor.section_id: ancestor for ancestor in stack}
            for prefix in cls._numbering_prefixes(section.heading_meta.numbering):
                numbered_ancestor = numbered_sections.get(prefix)
                if numbered_ancestor is not None:
                    combined[numbered_ancestor.section_id] = numbered_ancestor
            ancestors[section.section_id] = sorted(combined.values(), key=lambda item: order_by_id[item.section_id])
            stack.append(section)
            numbering = section.heading_meta.numbering
            if numbering:
                numbered_sections[numbering.strip().strip(".")] = section
        return ancestors

    @staticmethod
    def _selection_context(
        candidate_sections: list[PaperSection],
        ancestors_by_id: dict[str, list[PaperSection]],
    ) -> list[PaperSection]:
        candidate_ids = {section.section_id for section in candidate_sections}
        context: list[PaperSection] = []
        seen: set[str] = set()
        for section in candidate_sections:
            for ancestor in ancestors_by_id.get(section.section_id, []):
                if ancestor.section_id in candidate_ids or ancestor.section_id in seen:
                    continue
                context.append(ancestor)
                seen.add(ancestor.section_id)
        return context

    def section_selection_prompt(
        self,
        *,
        candidate_sections: list[PaperSection],
        context_sections: list[PaperSection],
    ) -> str:
        candidate_options = [self._section_option(section) for section in candidate_sections]
        if not context_sections:
            return (
                "Below is the list of extracted sections. Each item includes section_id, cleaned heading name, and heading_meta.\n"
                + json.dumps(candidate_options, ensure_ascii=False)
                + "\nFilter the list according to the rules and return ONLY a JSON array of objects with section_id in original order."
            )
        payload = {
            "context_sections": [self._section_option(section) for section in context_sections],
            "candidate_sections": candidate_options,
        }
        return (
            "Below is a bounded batch of extracted sections. Each item includes section_id, cleaned heading name, and heading_meta.\n"
            "Use context_sections only to apply parent-child hierarchy rules. Do not return context-only section IDs.\n"
            "Filter candidate_sections according to the rules and return ONLY a JSON array of objects with section_id in original order.\n"
            "Return only section_id values that appear in candidate_sections.\n"
            + json.dumps(payload, ensure_ascii=False)
        )

    def section_selection_batches(self, sections: list[PaperSection], system: str) -> list[SectionSelectionBatch]:
        budget_info = self.input_token_budget(system)
        if budget_info is None:
            return [SectionSelectionBatch(context_sections=[], candidate_sections=sections)]

        user_budget, encoder = budget_info
        ancestors_by_id = self.section_ancestors(sections)
        batches: list[SectionSelectionBatch] = []
        current: list[PaperSection] = []

        def prompt_for(candidate_sections: list[PaperSection]) -> str:
            return self.section_selection_prompt(
                candidate_sections=candidate_sections,
                context_sections=self._selection_context(candidate_sections, ancestors_by_id),
            )

        for section in sections:
            candidate = [*current, section]
            try:
                token_count = count_tokens(prompt_for(candidate), encoder)
            except Exception as exc:
                logger.warning("Token counting failed; section selection batching disabled: %s", exc)
                return [SectionSelectionBatch(context_sections=[], candidate_sections=sections)]
            if current and token_count > user_budget:
                batches.append(
                    SectionSelectionBatch(
                        context_sections=self._selection_context(current, ancestors_by_id),
                        candidate_sections=current,
                    )
                )
                current = [section]
                try:
                    single_token_count = count_tokens(prompt_for(current), encoder)
                except Exception as exc:
                    logger.warning("Token counting failed; section selection batching disabled: %s", exc)
                    return [SectionSelectionBatch(context_sections=[], candidate_sections=sections)]
                if single_token_count > user_budget:
                    logger.warning(
                        "Single section selection prompt for %s exceeds input budget; sending it unchanged",
                        section.section_id,
                    )
            else:
                current = candidate

        if current:
            batches.append(
                SectionSelectionBatch(
                    context_sections=self._selection_context(current, ancestors_by_id),
                    candidate_sections=current,
                )
            )
        return batches

    @staticmethod
    def _sentence_spans(text: str) -> list[str]:
        if not text:
            return []
        spans: list[str] = []
        start = 0
        for match in re.finditer(r"(?<=[.!?…。！？])\s+|\n\s*\n+", text):
            end = match.end()
            if end > start:
                spans.append(text[start:end])
            start = end
        if start < len(text):
            spans.append(text[start:])
        return [span for span in spans if span]

    @staticmethod
    def _token_split_section_text(
        section: PaperSection,
        text: str,
        *,
        budget: int,
        encoder: str,
    ) -> list[PaperSection]:
        codec = _get_encoder(encoder)
        tokens = codec.encode(text)
        if not tokens:
            return []
        if budget <= 0:
            return [section.model_copy(update={"text": text})]
        overlap = min(128, max(1, budget // 10))
        step = max(1, budget - overlap)
        return [
            section.model_copy(update={"text": codec.decode(tokens[start : start + budget])})
            for start in range(0, len(tokens), step)
        ]

    def _sentence_chunks(
        self,
        section: PaperSection,
        *,
        budget: int,
        encoder: str,
    ) -> list[PaperSection]:
        spans = self._sentence_spans(section.text)
        if not spans:
            return [section]

        chunks: list[PaperSection] = []
        current: list[str] = []

        for span in spans:
            span_tokens = count_tokens(span, encoder)
            if span_tokens > budget:
                if current:
                    chunks.append(section.model_copy(update={"text": "".join(current).strip()}))
                    current = []
                logger.warning(
                    "Section %s contains one sentence-like span with %s tokens, exceeding chunk budget=%s; "
                    "falling back to token split for that span",
                    section.section_id,
                    span_tokens,
                    budget,
                )
                chunks.extend(self._token_split_section_text(section, span, budget=budget, encoder=encoder))
                continue

            candidate = [*current, span]
            if current and count_tokens("".join(candidate), encoder) > budget:
                chunks.append(section.model_copy(update={"text": "".join(current).strip()}))
                overlap = current[-1:]
                current = [*overlap, span] if count_tokens("".join([*overlap, span]), encoder) <= budget else [span]
            else:
                current = candidate

        if current:
            chunks.append(section.model_copy(update={"text": "".join(current).strip()}))
        return chunks or [section]

    def section_chunks(self, section: PaperSection, system: str) -> list[PaperSection]:
        """Split a section into sentence-aware chunks that leave room for repair prompts."""
        settings = self._settings()
        if settings is None or not hasattr(settings, "context_window") or not hasattr(settings, "max_tokens"):
            return [section]
        encoder = getattr(settings, "encoder", "cl100k_base")
        total_input_budget = (
            getattr(settings, "context_window", 0)
            - getattr(settings, "max_tokens", 0)
            - 256
            - self.repair_reserve_tokens()
        )
        try:
            system_tokens = count_tokens(system, encoder)
        except Exception as exc:
            logger.warning(
                "Token encoder unavailable; using conservative character-based section chunks: %s",
                exc,
            )
            system_tokens = len(system)
            budget = total_input_budget - system_tokens
            if budget <= 0 or len(section.text) <= budget:
                return [section]
            overlap = min(512, max(1, budget // 10))
            step = max(1, budget - overlap)
            return [
                section.model_copy(update={"text": section.text[start : start + budget]})
                for start in range(0, len(section.text), step)
            ]

        budget = total_input_budget - system_tokens
        if budget <= 0 or count_tokens(section.text, encoder) <= budget:
            return [section]
        return self._sentence_chunks(section, budget=budget, encoder=encoder)

    @staticmethod
    def claim_extraction_prompt(section: PaperSection) -> str:
        return (
            "Analyze the following paper section and extract all verifiable factual claims:\n"
            + section.text
            + "\nReturn ONLY the JSON array as specified in the system instructions."
        )
