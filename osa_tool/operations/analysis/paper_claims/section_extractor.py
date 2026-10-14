from __future__ import annotations

import asyncio

from osa_tool.operations.analysis.artifacts import model_provenance
from osa_tool.operations.analysis.paper_claims.claim_extractor import AsyncModelHandler, ClaimExtractor
from osa_tool.operations.analysis.paper_claims.models import ClaimExtractionResult, PaperSection, PipelineOptions
from osa_tool.utils.prompts_builder import PromptLoader


async def extract_claims_from_sections(
    handler: AsyncModelHandler,
    sections: list[PaperSection],
    options: PipelineOptions | None = None,
    *,
    source: str | None = None,
    prompts: PromptLoader | None = None,
    show_progress: bool = True,
) -> ClaimExtractionResult:
    """Run claim extraction from already parsed sections without PDF/Marker parsing."""
    options = options or PipelineOptions()
    reset_provenance = getattr(handler, "reset_model_provenance", None)
    if callable(reset_provenance):
        reset_provenance()
    model_settings = getattr(handler, "model_settings", None)
    configured_model = getattr(model_settings, "model", None)
    extraction = await ClaimExtractor(
        handler,
        prompts=prompts,
        max_retries=options.max_retries,
        dedup_batch_size=options.dedup_batch_size,
        show_progress=show_progress,
    ).extract(sections, source=source, model=configured_model)
    provenance = model_provenance(handler, configured=configured_model)
    extraction.meta.configured_model = provenance.configured
    extraction.meta.models_used = provenance.used or ([extraction.meta.model] if extraction.meta.model else [])
    if extraction.meta.models_used:
        extraction.meta.model = extraction.meta.models_used[-1]
    return extraction


def run_claim_extraction_from_sections(
    handler: AsyncModelHandler,
    sections: list[PaperSection],
    options: PipelineOptions | None = None,
    *,
    source: str | None = None,
    prompts: PromptLoader | None = None,
    show_progress: bool = True,
) -> ClaimExtractionResult:
    """Synchronous wrapper around :func:`extract_claims_from_sections`."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            extract_claims_from_sections(
                handler,
                sections,
                options,
                source=source,
                prompts=prompts,
                show_progress=show_progress,
            )
        )
    raise RuntimeError(
        "run_claim_extraction_from_sections() cannot be used inside an active event loop; "
        "await extract_claims_from_sections() instead"
    )
