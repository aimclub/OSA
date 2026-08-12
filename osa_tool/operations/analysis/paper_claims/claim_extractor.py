from __future__ import annotations

from typing import Any, Callable, Protocol

from pydantic import TypeAdapter, ValidationError
from rich.progress import track

from osa_tool.operations.analysis.paper_claims.claim_deduplicator import ClaimDeduplicator
from osa_tool.operations.analysis.paper_claims.claim_input_planner import ClaimInputPlanner
from osa_tool.operations.analysis.paper_claims.claim_schemas import (
    ClaimCandidateResponse,
    SelectedSectionResponse,
)
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
from osa_tool.utils.token_counter import count_tokens, truncate_to_tokens


class AsyncModelHandler(Protocol):
    async def async_request(self, prompt: str, system_message: str | None = None, retry_delay: float = 1) -> str: ...


class ClaimExtractor:
    """Run the three claim-extraction stages for one parsed report."""

    def __init__(
        self,
        handler: AsyncModelHandler,
        *,
        prompts: PromptLoader | None = None,
        max_retries: int = 5,
        dedup_batch_size: int = 100,
    ) -> None:
        if max_retries <= 0:
            raise ValueError("max_retries must be greater than zero")
        if dedup_batch_size < 2:
            raise ValueError("dedup_batch_size must be at least 2")
        self.handler = handler
        self.prompts = prompts or PromptLoader()
        self.max_retries = max_retries
        self.dedup_batch_size = dedup_batch_size
        self._input_planner = ClaimInputPlanner(lambda: getattr(self.handler, "model_settings", None))
        self._deduplicator = ClaimDeduplicator(
            request_validated=self._request_validated,
            input_planner=self._input_planner,
            deduplication_system=self.prompts.get("paper_claims.deduplication_system"),
            dedup_batch_size=dedup_batch_size,
        )

    def _repair_prompt(
        self,
        *,
        error: str,
        response: str,
        original_prompt: str,
        system: str,
    ) -> str:
        template = self.prompts.get("paper_claims.repair")
        full_prompt = PromptBuilder.render(
            template,
            error=error,
            response=response,
            original_prompt=original_prompt,
        )
        budget_info = self._input_planner.input_token_budget(system)
        if budget_info is None:
            return full_prompt

        user_budget, encoder = budget_info
        try:
            if count_tokens(full_prompt, encoder) <= user_budget:
                return full_prompt
        except Exception as exc:
            logger.warning("Token counting failed; using unbounded repair prompt: %s", exc)
            return full_prompt

        empty_template_tokens = count_tokens(
            PromptBuilder.render(template, error="", response="", original_prompt=""),
            encoder,
        )
        error_tokens = count_tokens(error, encoder)
        error_limit = max(0, min(error_tokens, 1024, user_budget // 4))
        bounded_error = error if error_tokens <= error_limit else truncate_to_tokens(error, error_limit, encoder)
        bounded_error_tokens = count_tokens(bounded_error, encoder)
        remaining = max(0, user_budget - empty_template_tokens - bounded_error_tokens)
        response_limit = max(0, min(1024, remaining // 4))
        bounded_response = truncate_to_tokens(response, response_limit, encoder)
        bounded_response_tokens = count_tokens(bounded_response, encoder)
        original_limit = max(0, remaining - bounded_response_tokens)
        bounded_original_prompt = truncate_to_tokens(original_prompt, original_limit, encoder, mode="start")
        return PromptBuilder.render(
            template,
            error=bounded_error,
            response=bounded_response,
            original_prompt=bounded_original_prompt,
        )

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
            try:
                raw = await self.handler.async_request(current_prompt, system)
            except Exception as exc:
                raise ClaimExtractionError(f"{request_name}: model request failed: {exc}") from exc
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
                if attempt < self.max_retries:
                    logger.info("%s: response validation failed, preparing repair request", request_name)
                else:
                    logger.warning("%s: response validation failed after final attempt", request_name)
                current_prompt = self._repair_prompt(
                    error=str(exc),
                    response=str(raw),
                    original_prompt=original_prompt,
                    system=system,
                )
        raise ClaimExtractionError(f"LLM response remained invalid after {self.max_retries} attempts: {last_error}")

    async def _request_claim_candidates(
        self,
        prompt: str,
        system: str,
        adapter: TypeAdapter[ClaimCandidateResponse],
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
            try:
                raw = await self.handler.async_request(current_prompt, system)
            except Exception as exc:
                raise ClaimExtractionError(f"{request_name}: model request failed: {exc}") from exc
            logger.debug("Raw response:\n%s", raw)
            try:
                data = JsonProcessor.parse(str(raw), expected_type=list)
                if not isinstance(data, list):
                    raise TypeError(f"Expected list, got {type(data)}")
            except (JsonParseError, TypeError) as exc:
                last_error = exc
                if attempt < self.max_retries:
                    logger.info("%s: response validation failed, preparing repair request", request_name)
                else:
                    logger.warning("%s: response validation failed after final attempt", request_name)
                current_prompt = self._repair_prompt(
                    error=str(exc),
                    response=str(raw),
                    original_prompt=original_prompt,
                    system=system,
                )
                continue

            parsed: list[ClaimCandidateResponse] = []
            invalid: list[str] = []
            for index, item in enumerate(data, start=1):
                try:
                    parsed.append(adapter.validate_python(item))
                except ValidationError as exc:
                    invalid.append(f"claim #{index}: schema validation failed: {exc}")

            valid, source_invalid = partition_valid_claim_candidates(parsed, section=section)
            invalid.extend(source_invalid)
            if not invalid:
                logger.info("%s: response validated", request_name)
                logger.debug("Parsed response:\n%s", valid)
                return valid

            last_error = ValueError("; ".join(invalid))
            if attempt < self.max_retries:
                logger.info("%s: response validation failed, preparing repair request", request_name)
                current_prompt = self._repair_prompt(
                    error=str(last_error),
                    response=str(raw),
                    original_prompt=original_prompt,
                    system=system,
                )
                continue

            for error in invalid:
                logger.warning("%s: dropping invalid claim after final attempt: %s", request_name, error)
            logger.info("%s: kept %s/%s claims after dropping invalid claims", request_name, len(valid), len(parsed))
            logger.debug("Parsed response after dropping invalid claims:\n%s", valid)
            return valid

        raise ClaimExtractionError(f"LLM response remained invalid after {self.max_retries} attempts: {last_error}")

    async def _step_1_select_sections(self, sections: list[PaperSection]) -> list[str]:
        """Select claim-bearing sections while preserving their source order."""
        logger.info("Claim extraction step 1/3: selecting relevant sections from %s sections", len(sections))
        system = self.prompts.get("paper_claims.section_filter_system")
        batches = self._input_planner.section_selection_batches(sections, system)
        if len(batches) > 1:
            logger.info(
                "Claim extraction step 1/3: split section selection into %s batches to fit model input budget",
                len(batches),
            )

        selected_ids: list[str] = []
        for batch_index, batch in enumerate(batches, start=1):
            candidate_by_id = {section.section_id: section for section in batch.candidate_sections}
            request_name = "Section selection"
            if len(batches) > 1:
                request_name = f"Section selection batch {batch_index}/{len(batches)}"

            def validate_sections(items: list[SelectedSectionResponse]) -> None:
                ids = [item.section_id for item in items]
                if len(ids) != len(set(ids)) or any(item not in candidate_by_id for item in ids):
                    raise ValueError("Selection contains duplicate or unknown section IDs")

            selected = await self._request_validated(
                self._input_planner.section_selection_prompt(
                    candidate_sections=batch.candidate_sections,
                    context_sections=batch.context_sections,
                ),
                system,
                TypeAdapter(list[SelectedSectionResponse]),
                validate_sections,
                request_name=request_name,
            )
            selected_ids.extend(item.section_id for item in selected)
            logger.info(
                "%s completed: selected %s/%s candidate sections",
                request_name,
                len(selected),
                len(batch.candidate_sections),
            )

        section_by_id = {section.section_id: section for section in sections}
        if len(selected_ids) != len(set(selected_ids)) or any(item not in section_by_id for item in selected_ids):
            raise ClaimExtractionError("Section selection contains duplicate or unknown section IDs after merging")
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
        claim_adapter = TypeAdapter(ClaimCandidateResponse)
        claim_system = self.prompts.get("paper_claims.claim_extraction_system")
        for section_id in track(selected_section_ids, description="Extracting section claims"):
            section = section_by_id[section_id]
            if not section.text.strip():
                logger.info("Skipping empty selected section %s (%s)", section.section_id, section.name)
                continue
            logger.info("Extracting claims from section %s (%s)", section.section_id, section.name)

            section_chunks = self._input_planner.section_chunks(section, claim_system)
            if len(section_chunks) > 1:
                logger.info(
                    "Section %s split into %s extraction chunks to fit model input budget",
                    section.section_id,
                    len(section_chunks),
                )
            section_claims = 0
            for chunk_index, section_chunk in enumerate(section_chunks, start=1):
                request_name = f"Claim extraction for section {section.section_id}"
                if len(section_chunks) > 1:
                    request_name = (
                        f"Claim extraction for section {section.section_id} chunk {chunk_index}/{len(section_chunks)}"
                    )

                try:
                    candidates = await self._request_claim_candidates(
                        self._input_planner.claim_extraction_prompt(section_chunk),
                        claim_system,
                        claim_adapter,
                        section=section_chunk,
                        request_name=request_name,
                    )
                except ClaimExtractionError as exc:
                    logger.warning(
                        "Skipping section %s (%s) chunk %s/%s after claim extraction failed: %s",
                        section.section_id,
                        section.name,
                        chunk_index,
                        len(section_chunks),
                        exc,
                    )
                    continue
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
                section_claims += len(candidates)
                if len(section_chunks) > 1:
                    logger.info(
                        "Section %s chunk %s/%s completed: extracted %s claims",
                        section.section_id,
                        chunk_index,
                        len(section_chunks),
                        len(candidates),
                    )
            logger.info(
                "Section %s completed: extracted %s claims from %s chunk(s)",
                section.section_id,
                section_claims,
                len(section_chunks),
            )
        logger.info("Claim extraction step 2/3 completed: extracted %s claims", len(claims))
        return claims

    async def _step_3_deduplicate_claims(
        self,
        claims: list[ExtractedClaim],
    ) -> tuple[list[ExtractedClaim], list[DedupSelection]]:
        return await self._deduplicator.deduplicate(claims)

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
        extraction_model = getattr(self.handler, "last_successful_model", None) or model
        filtered_claims, selections = await self._step_3_deduplicate_claims(extracted_claims)
        logger.info("Three-step claim extraction completed: final_claims=%s", len(filtered_claims))

        return ClaimExtractionResult(
            claims=filtered_claims,
            deduplication=selections,
            selected_section_ids=selected_ids,
            meta=ExtractionMetadata(
                source=source,
                model=extraction_model,
                filtered_claims=len(filtered_claims),
                step3_input_count=len(extracted_claims),
                step3_output_count=len(selections),
            ),
        )
