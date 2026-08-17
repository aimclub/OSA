from __future__ import annotations

import json
import re
import unicodedata
from functools import partial
from typing import Any, Callable, Protocol

from pydantic import BaseModel, ConfigDict, TypeAdapter, ValidationError

from osa_tool.operations.analysis.paper_claims.exceptions import ClaimExtractionError
from osa_tool.operations.analysis.paper_claims.models import (
    ClaimCategory,
    ClaimExtractionResult,
    DedupSelection,
    ExtractedClaim,
    ExtractionMetadata,
    PaperSection,
    Verifiability,
)
from osa_tool.utils.prompts_builder import PromptBuilder, PromptLoader
from osa_tool.utils.response_cleaner import JsonParseError, JsonProcessor

_INVISIBLE_CHARACTERS = "\u00ad\u200b\u200c\u200d\u2060\ufeff"
_INVISIBLE_GAP_PATTERN = f"[{_INVISIBLE_CHARACTERS}]*"
_WORD_GAP_PATTERN = f"(?:\\s|[{_INVISIBLE_CHARACTERS}])+"


def _find_original_source_text(section_text: str, original_text: str) -> str | None:
    """Return the exact source span while tolerating layout-only character differences."""
    if original_text in section_text:
        return original_text

    candidate = original_text.strip().translate({ord(character): None for character in _INVISIBLE_CHARACTERS})
    if not candidate:
        return None

    tokens = re.split(r"\s+", candidate)
    token_patterns = [
        _INVISIBLE_GAP_PATTERN.join(re.escape(character) for character in token) for token in tokens if token
    ]
    if not token_patterns:
        return None

    match = re.search(_WORD_GAP_PATTERN.join(token_patterns), section_text)
    return match.group(0) if match else None


def _section_text_preview(text: str, limit: int = 2_000) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return f"{text[:half]}\n... <{len(text) - limit} characters omitted> ...\n{text[-half:]}"


def _dominant_script(text: str) -> str | None:
    """Return the dominant Unicode script for letters in text."""
    scripts: dict[str, int] = {}
    script_markers = {
        "LATIN": ("LATIN",),
        "CYRILLIC": ("CYRILLIC",),
        "EAST_ASIAN": ("CJK", "HIRAGANA", "KATAKANA", "HANGUL"),
        "ARABIC": ("ARABIC",),
        "HEBREW": ("HEBREW",),
    }
    for character in text:
        if not character.isalpha():
            continue
        unicode_name = unicodedata.name(character, "")
        script = next(
            (script for script, markers in script_markers.items() if any(marker in unicode_name for marker in markers)),
            None,
        )
        if script:
            scripts[script] = scripts.get(script, 0) + 1
    return max(scripts, key=scripts.get) if scripts else None


class AsyncModelHandler(Protocol):
    async def async_request(self, prompt: str, system_message: str | None = None, retry_delay: float = 1) -> str: ...


class _StrictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _SelectedSection(_StrictResponse):
    section_id: str


class _ClaimCandidate(_StrictResponse):
    claim: str
    original_text: str
    category: ClaimCategory
    value: str | None = None
    verifiability: Verifiability


def _validate_source_text(items: list[_ClaimCandidate], *, section: PaperSection) -> None:
    """Validate candidate quotations and restore their exact source representation."""
    for item in items:
        source_text = _find_original_source_text(section.text, item.original_text)
        if source_text is None:
            logger.debug(
                "Source-text validation failed for section %s. Candidate=%r; section_text=%r",
                section.section_id,
                item.original_text,
                section.text,
            )
            raise ValueError(
                f"original_text is not present in section {section.section_id}. "
                f"original_text={item.original_text!r}; "
                f"section_text_preview={_section_text_preview(section.text)!r}; "
                f"section_text_length={len(section.text)}"
            )
        item.original_text = source_text
        source_script = _dominant_script(source_text)
        claim_script = _dominant_script(item.claim)
        if source_script and claim_script and source_script != claim_script:
            raise ValueError(
                "claim must use the same language script as original_text. "
                f"claim_script={claim_script}; original_text_script={source_script}; "
                f"claim={item.claim!r}; original_text={source_text!r}"
            )


class ClaimExtractor:
    def __init__(
        self,
        handler: AsyncModelHandler,
        *,
        prompts: PromptLoader | None = None,
        max_retries: int = 5,
    ) -> None:
        if max_retries <= 0:
            raise ValueError("max_retries must be greater than zero")
        self.handler = handler
        self.prompts = prompts or PromptLoader()
        self.max_retries = max_retries

    async def _request_validated(
        self,
        prompt: str,
        system: str,
        adapter: TypeAdapter[Any],
        validator: Callable[[Any], None] | None = None,
    ) -> Any:
        logger.debug("System prompt:\n%s", system)
        logger.debug("User prompt:\n%s", prompt)
        current_prompt = prompt
        original_prompt = prompt
        last_error: Exception | None = None
        for _ in range(self.max_retries):
            raw = await self.handler.async_request(current_prompt, system)
            try:
                data = JsonProcessor.parse(str(raw), expected_type=list)
                parsed = adapter.validate_python(data)
                if validator:
                    validator(parsed)
                return parsed
            except (JsonParseError, ValueError, TypeError, ValidationError) as exc:
                last_error = exc
                current_prompt = PromptBuilder.render(
                    self.prompts.get("paper_claims.repair"),
                    error=str(exc),
                    response=str(raw),
                    original_prompt=original_prompt,
                )
        raise ClaimExtractionError(f"LLM response remained invalid after {self.max_retries} attempts: {last_error}")

    async def _step_1_select_sections(self, sections: list[PaperSection]) -> list[str]:
        """Select claim-bearing sections while preserving their source order."""
        section_by_id = {section.section_id: section for section in sections}
        section_options = [
            {
                "section_id": section.section_id,
                "name": section.name,
                "heading_meta": section.heading_meta.model_dump(mode="json"),
            }
            for section in sections
        ]

        def validate_sections(items: list[_SelectedSection]) -> None:
            ids = [item.section_id for item in items]
            if len(ids) != len(set(ids)) or any(item not in section_by_id for item in ids):
                raise ValueError("Selection contains duplicate or unknown section IDs")

        selected = await self._request_validated(
            "Below is the list of extracted sections. Each item includes section_id, cleaned heading name, and heading_meta.\n"
            + json.dumps(section_options, ensure_ascii=False)
            + "\nFilter the list according to the rules and return ONLY a JSON array of objects with section_id in original order.",
            self.prompts.get("paper_claims.section_filter_system"),
            TypeAdapter(list[_SelectedSection]),
            validate_sections,
        )
        selected_ids = [item.section_id for item in selected]
        selected_set = set(selected_ids)
        return [section.section_id for section in sections if section.section_id in selected_set]

    async def _step_2_extract_claims(
        self,
        sections: list[PaperSection],
        selected_section_ids: list[str],
    ) -> list[ExtractedClaim]:
        """Extract and validate atomic claims from each selected section."""
        section_by_id = {section.section_id: section for section in sections}
        claims: list[ExtractedClaim] = []
        claim_adapter = TypeAdapter(list[_ClaimCandidate])
        for section_id in selected_section_ids:
            section = section_by_id[section_id]
            if not section.text.strip():
                continue

            def validate_source_text(items: list[_ClaimCandidate]) -> None:
                for item in items:
                    if item.original_text not in section.text:
                        raise ValueError(
                            f"original_text is not present in section {section.section_id}: {item.original_text!r}"
                        )

            candidates = await self._request_validated(
                "Analyze the following paper section and extract all verifiable factual claims:\n"
                + section.text
                + "\nReturn ONLY the JSON array as specified in the system instructions.",
                self.prompts.get("paper_claims.claim_extraction_system"),
                claim_adapter,
                validate_source_text,
            )
            for candidate in candidates:
                claims.append(
                    ExtractedClaim(
                        claim_id=f"c{len(claims) + 1:04d}",
                        **candidate.model_dump(),
                        section_id=section.section_id,
                        section_name=section.name,
                        section_heading_raw=section.heading_meta.raw,
                    )
                )
        return claims

    async def _step_3_deduplicate_claims(
        self,
        claims: list[ExtractedClaim],
    ) -> tuple[list[ExtractedClaim], list[DedupSelection]]:
        """Deduplicate claims, retain contradictions, and enrich kept claims."""
        if not claims:
            return [], []

        dedup_input = [{"claim_id": claim.claim_id, "claim": claim.claim} for claim in claims]
        claims_by_id = {claim.claim_id: claim for claim in claims}

        def validate_dedup(items: list[DedupSelection]) -> None:
            ids = [item.claim_id for item in items]
            if len(ids) != len(set(ids)) or any(item not in claims_by_id for item in ids):
                raise ValueError("Deduplication contains duplicate or unknown claim IDs")
            rewritten = [item.claim_id for item in items if item.claim != claims_by_id[item.claim_id].claim]
            if rewritten:
                raise ValueError(
                    "Deduplication must copy claim text verbatim; rewritten claim IDs: " + ", ".join(rewritten)
                )

        selections = await self._request_validated(
            "Below is the JSON array of claims extracted from the report sections. Apply the deduplication and contradiction rules.\n"
            + json.dumps(dedup_input, ensure_ascii=False)
            + "\nReturn ONLY the final processed JSON array.",
            self.prompts.get("paper_claims.deduplication_system"),
            TypeAdapter(list[DedupSelection]),
            validate_dedup,
        )

        selection_by_id = {item.claim_id: item for item in selections}
        filtered = [
            claim.model_copy(update={"contradiction": selection_by_id[claim.claim_id].contradiction})
            for claim in claims
            if claim.claim_id in selection_by_id
        ]
        return filtered, selections

    async def extract(
        self,
        sections: list[PaperSection],
        *,
        source: str | None = None,
        model: str | None = None,
    ) -> ClaimExtractionResult:
        """Run section selection, claim extraction, and deduplication."""
        if not sections:
            raise ClaimExtractionError("At least one paper section is required")

        selected_ids = await self._step_1_select_sections(sections)
        extracted_claims = await self._step_2_extract_claims(sections, selected_ids)
        filtered_claims, selections = await self._step_3_deduplicate_claims(extracted_claims)
        logger.info("Three-step claim extraction completed: final_claims=%s", len(filtered_claims))
        actual_model = getattr(self.handler, "last_successful_model", None) or model

        return ClaimExtractionResult(
            claims=filtered_claims,
            deduplication=selections,
            selected_section_ids=selected_ids,
            meta=ExtractionMetadata(
                source=source,
                model=actual_model,
                filtered_claims=len(filtered_claims),
                step3_input_count=len(extracted_claims),
                step3_output_count=len(selections),
            ),
        )
