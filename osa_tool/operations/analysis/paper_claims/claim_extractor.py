from __future__ import annotations

import json
from typing import Any, Callable, Protocol

from pydantic import TypeAdapter, ValidationError
from rich.progress import track

from osa_tool.operations.analysis.paper_claims.claim_schemas import ClaimCandidateResponse, SelectedSectionResponse
from osa_tool.operations.analysis.paper_claims.claim_validation import partition_valid_claim_candidates
from osa_tool.operations.analysis.paper_claims.exceptions import ClaimExtractionError
from osa_tool.operations.analysis.paper_claims.models import (
    ClaimExtractionResult,
    DedupSelection,
    ExtractedClaim,
    ExtractionMetadata,
    PaperSection,
)
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder, PromptLoader
from osa_tool.utils.response_cleaner import JsonParseError, JsonProcessor


class AsyncModelHandler(Protocol):
    async def async_request(self, prompt: str, system_message: str | None = None, retry_delay: float = 1) -> str: ...


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
        request_name: str = "LLM request",
    ) -> Any:
        logger.debug("System prompt:\n%s", system)
        logger.debug("User prompt:\n%s", prompt)
        current_prompt = prompt
        original_prompt = prompt
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            logger.info("%s: sending request (attempt %s/%s)", request_name, attempt, self.max_retries)
            raw = await self.handler.async_request(current_prompt, system)
            logger.debug("Raw response:\n%s", raw)
            try:
                data = JsonProcessor.parse(str(raw), expected_type=list)
                parsed = adapter.validate_python(data)
                if validator:
                    validator(parsed)
                logger.info("%s: response validated", request_name)
                logger.debug("Parsed response:\n%s", parsed)
                return parsed
            except (JsonParseError, ValueError, TypeError, ValidationError) as exc:
                last_error = exc
                logger.info("%s: response validation failed, preparing repair request", request_name)
                current_prompt = PromptBuilder.render(
                    self.prompts.get("paper_claims.repair"),
                    error=str(exc),
                    response=str(raw),
                    original_prompt=original_prompt,
                )
        raise ClaimExtractionError(f"LLM response remained invalid after {self.max_retries} attempts: {last_error}")

    async def _request_claim_candidates(
        self,
        prompt: str,
        system: str,
        adapter: TypeAdapter[list[ClaimCandidateResponse]],
        *,
        section: PaperSection,
        request_name: str,
    ) -> list[ClaimCandidateResponse]:
        logger.debug("System prompt:\n%s", system)
        logger.debug("User prompt:\n%s", prompt)
        current_prompt = prompt
        original_prompt = prompt
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            logger.info("%s: sending request (attempt %s/%s)", request_name, attempt, self.max_retries)
            raw = await self.handler.async_request(current_prompt, system)
            logger.debug("Raw response:\n%s", raw)
            try:
                data = JsonProcessor.parse(str(raw), expected_type=list)
                parsed = adapter.validate_python(data)
            except (JsonParseError, TypeError, ValidationError) as exc:
                last_error = exc
                logger.info("%s: response validation failed, preparing repair request", request_name)
                current_prompt = PromptBuilder.render(
                    self.prompts.get("paper_claims.repair"),
                    error=str(exc),
                    response=str(raw),
                    original_prompt=original_prompt,
                )
                continue

            valid, invalid = partition_valid_claim_candidates(parsed, section=section)
            if not invalid:
                logger.info("%s: response validated", request_name)
                logger.debug("Parsed response:\n%s", valid)
                return valid

            last_error = ValueError("; ".join(invalid))
            if attempt < self.max_retries:
                logger.info("%s: response validation failed, preparing repair request", request_name)
                current_prompt = PromptBuilder.render(
                    self.prompts.get("paper_claims.repair"),
                    error=str(last_error),
                    response=str(raw),
                    original_prompt=original_prompt,
                )
                continue

            for error in invalid:
                logger.info("%s: dropping invalid claim after final attempt: %s", request_name, error)
            logger.info(
                "%s: kept %s/%s claims after dropping invalid claims",
                request_name,
                len(valid),
                len(parsed),
            )
            logger.debug("Parsed response after dropping invalid claims:\n%s", valid)
            return valid

        raise ClaimExtractionError(f"LLM response remained invalid after {self.max_retries} attempts: {last_error}")

    async def _step_1_select_sections(self, sections: list[PaperSection]) -> list[str]:
        """Select claim-bearing sections while preserving their source order."""
        logger.info("Claim extraction step 1/3: selecting relevant sections from %s sections", len(sections))
        section_by_id = {section.section_id: section for section in sections}
        section_options = [
            {
                "section_id": section.section_id,
                "name": section.name,
                "heading_meta": section.heading_meta.model_dump(mode="json"),
            }
            for section in sections
        ]

        def validate_sections(items: list[SelectedSectionResponse]) -> None:
            ids = [item.section_id for item in items]
            if len(ids) != len(set(ids)) or any(item not in section_by_id for item in ids):
                raise ValueError("Selection contains duplicate or unknown section IDs")

        selected = await self._request_validated(
            "Below is the list of extracted sections. Each item includes section_id, cleaned heading name, and heading_meta.\n"
            + json.dumps(section_options, ensure_ascii=False)
            + "\nFilter the list according to the rules and return ONLY a JSON array of objects with section_id in original order.",
            self.prompts.get("paper_claims.section_filter_system"),
            TypeAdapter(list[SelectedSectionResponse]),
            validate_sections,
            request_name="Section selection",
        )
        selected_ids = [item.section_id for item in selected]
        selected_set = set(selected_ids)
        ordered_ids = [section.section_id for section in sections if section.section_id in selected_set]
        logger.info("Claim extraction step 1/3 completed: selected %s sections", len(ordered_ids))
        return ordered_ids

    async def _step_2_extract_claims(
        self,
        sections: list[PaperSection],
        selected_section_ids: list[str],
    ) -> list[ExtractedClaim]:
        """Extract and validate atomic claims from each selected section."""
        logger.info(
            "Claim extraction step 2/3: extracting claims from %s selected sections",
            len(selected_section_ids),
        )
        section_by_id = {section.section_id: section for section in sections}
        claims: list[ExtractedClaim] = []
        claim_adapter = TypeAdapter(list[ClaimCandidateResponse])
        for section_id in track(selected_section_ids, description="Extracting section claims"):
            section = section_by_id[section_id]
            if not section.text.strip():
                logger.info("Skipping empty selected section %s (%s)", section.section_id, section.name)
                continue
            logger.info("Extracting claims from section %s (%s)", section.section_id, section.name)

            candidates = await self._request_claim_candidates(
                "Analyze the following paper section and extract all verifiable factual claims:\n"
                + section.text
                + "\nReturn ONLY the JSON array as specified in the system instructions.",
                self.prompts.get("paper_claims.claim_extraction_system"),
                claim_adapter,
                section=section,
                request_name=f"Claim extraction for section {section.section_id}",
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
            logger.info(
                "Section %s completed: extracted %s claims",
                section.section_id,
                len(candidates),
            )
        logger.info("Claim extraction step 2/3 completed: extracted %s claims", len(claims))
        return claims

    async def _step_3_deduplicate_claims(
        self,
        claims: list[ExtractedClaim],
    ) -> tuple[list[ExtractedClaim], list[DedupSelection]]:
        """Deduplicate claims, retain contradictions, and enrich kept claims."""
        if not claims:
            logger.info("Claim extraction step 3/3 skipped: no claims to deduplicate")
            return [], []

        logger.info("Claim extraction step 3/3: deduplicating %s claims", len(claims))
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
            request_name="Claim deduplication",
        )

        selection_by_id = {item.claim_id: item for item in selections}
        filtered = [
            claim.model_copy(update={"contradiction": selection_by_id[claim.claim_id].contradiction})
            for claim in claims
            if claim.claim_id in selection_by_id
        ]
        logger.info("Claim extraction step 3/3 completed: retained %s claims", len(filtered))
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

        logger.info("Starting three-step claim extraction")
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
