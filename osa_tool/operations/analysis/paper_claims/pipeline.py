from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from osa_tool.operations.analysis.artifacts import (
    ModelProvenance,
    StageReportMetadata,
    write_stage_report,
)
from osa_tool.operations.analysis.paper_claims.claim_extractor import AsyncModelHandler
from osa_tool.operations.analysis.paper_claims.io import (
    export_loaded_claims,
    export_section_extraction,
    load_claims_json,
    load_sections_json,
    model_provenance_for_loaded,
)
from osa_tool.operations.analysis.paper_claims.marker_converter import MarkerDocumentConverter
from osa_tool.operations.analysis.paper_claims.models import (
    ClaimExtractionResult,
    LoadedClaimsArtifact,
    LoadedSectionsArtifact,
    PaperSection,
    PipelineOptions,
    PipelineResult,
)
from osa_tool.operations.analysis.paper_claims.pdf_splitter import PdfChunker
from osa_tool.operations.analysis.paper_claims.section_extractor import extract_claims_from_sections
from osa_tool.operations.analysis.paper_claims.section_parser import MarkdownSectionParser
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptLoader


class PaperClaimPipeline:
    def __init__(
        self,
        handler: AsyncModelHandler,
        *,
        converter: MarkerDocumentConverter | None = None,
        section_parser: MarkdownSectionParser | None = None,
        prompts: PromptLoader | None = None,
    ) -> None:
        self.handler = handler
        self.converter = converter or MarkerDocumentConverter()
        self.section_parser = section_parser or MarkdownSectionParser()
        self.prompts = prompts

    async def arun(
        self,
        pdf_path: Path,
        options: PipelineOptions | None = None,
        *,
        show_progress: bool = True,
    ) -> PipelineResult:
        options = options or PipelineOptions()
        pdf_path = Path(pdf_path)
        logger.info("Paper claims pipeline started for %s", pdf_path)
        logger.info("Stage 1/4: starting PDF splitting")
        with PdfChunker() as chunker:
            chunks = chunker.split(
                pdf_path,
                pages_per_chunk=options.pages_per_chunk,
                show_progress=show_progress,
            )
            logger.info("Stage 1/4 completed: PDF split into %s chunks", len(chunks))
            logger.info("Stage 2/4: starting Marker conversion")
            converted = self.converter.convert(chunks, options.marker, show_progress=show_progress)
            logger.info(
                "Stage 2/4 completed: Marker conversion finished (cache_hit=%s)",
                converted.cache_hit,
            )
        logger.info("Stage 3/4: parsing converted Markdown into sections")
        sections = self.section_parser.parse(converted.markdown)
        logger.info("Stage 3/4 completed: parsed %s sections", len(sections))
        model_settings = getattr(self.handler, "model_settings", None)
        configured_model = getattr(model_settings, "model", None)
        logger.info("Stage 4/4: starting claim extraction with model %s", configured_model or "unknown")
        extraction = await self.extract_from_sections(
            sections,
            options,
            source=str(converted.source_path),
            show_progress=show_progress,
        )
        logger.info(
            "Stage 4/4 completed: model=%s; selected_sections=%s; extracted_before_dedup=%s; final_claims=%s",
            extraction.meta.model or "unknown",
            len(extraction.selected_section_ids),
            extraction.meta.step3_input_count,
            len(extraction.claims),
        )
        logger.info("Paper claims pipeline completed for %s", pdf_path)
        return PipelineResult(converted_document=converted, sections=sections, extraction=extraction)

    async def extract_from_sections(
        self,
        sections: list[PaperSection],
        options: PipelineOptions | None = None,
        *,
        source: str | None = None,
        show_progress: bool = True,
    ) -> ClaimExtractionResult:
        """Run claim extraction from parsed sections with this pipeline's handler and prompts."""
        return await extract_claims_from_sections(
            self.handler,
            sections,
            options,
            source=source,
            prompts=self.prompts,
            show_progress=show_progress,
        )

    def run(
        self,
        pdf_path: Path,
        options: PipelineOptions | None = None,
        *,
        show_progress: bool = True,
    ) -> PipelineResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(pdf_path, options, show_progress=show_progress))
        raise RuntimeError("PaperClaimPipeline.run() cannot be used inside an active event loop; await arun() instead")

    @staticmethod
    def export(
        result: PipelineResult,
        output_dir: Path,
        *,
        legacy: bool = False,
        include_debug: bool = False,
    ) -> Path:
        destination = Path(output_dir)
        logger.info("Exporting paper claims artifacts to %s", destination)
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "document.md").write_text(result.converted_document.markdown, encoding="utf-8")
        (destination / "sections.json").write_text(
            json.dumps([item.model_dump(mode="json") for item in result.sections], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        payload = (
            result.to_legacy_dict(include_debug=include_debug) if legacy else result.extraction.model_dump(mode="json")
        )
        output_path = destination / ("claims_legacy.json" if legacy else "claims.json")
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        extraction = result.extraction
        write_stage_report(
            destination,
            meta=StageReportMetadata(
                source={"paper": {"kind": "pdf", "path": str(result.converted_document.source_path)}},
                model=PaperClaimPipeline.model_provenance_for_extraction(result),
            ),
            result=extraction.model_dump(mode="json"),
        )
        logger.info("Paper claims export completed: %s", output_path)
        return output_path

    @staticmethod
    def load_claims_json(path: Path) -> LoadedClaimsArtifact:
        """Accept typed ``claims.json``, legacy ``claims_legacy.json``, or a bare list."""
        return load_claims_json(path)

    @staticmethod
    def export_loaded_claims(loaded: LoadedClaimsArtifact, output_dir: Path) -> Path:
        """Materialize imported claims as a resumable artifact and canonical stage report."""
        return export_loaded_claims(loaded, output_dir)

    @staticmethod
    def load_sections_json(path: Path) -> LoadedSectionsArtifact:
        """Accept parsed PaperSection JSON as a bare list or a ``sections`` envelope."""
        return load_sections_json(path)

    @staticmethod
    def export_section_extraction(
        extraction: ClaimExtractionResult,
        sections: list[PaperSection],
        output_dir: Path,
        *,
        source_kind: str,
        source_path: Path,
        model: ModelProvenance,
        upstream_meta: dict[str, Any] | None = None,
    ) -> Path:
        """Export claims extracted from parsed sections."""
        return export_section_extraction(
            extraction,
            sections,
            output_dir,
            source_kind=source_kind,
            source_path=source_path,
            model=model,
            upstream_meta=upstream_meta,
        )

    @staticmethod
    def model_provenance_for_extraction(result: PipelineResult) -> ModelProvenance:
        """Return claim-extraction model provenance stored in a pipeline result."""
        metadata = result.extraction.meta
        configured = getattr(metadata, "configured_model", None)
        if not isinstance(configured, str):
            configured = getattr(metadata, "model", None)
        if not isinstance(configured, str):
            configured = None
        recorded = getattr(metadata, "models_used", [])
        used = [model for model in recorded if isinstance(model, str) and model] if isinstance(recorded, list) else []
        model = getattr(metadata, "model", None)
        if not used and isinstance(model, str) and model:
            used = [model]
        return ModelProvenance(configured=configured, used=list(dict.fromkeys(used)))

    @staticmethod
    def model_provenance_for_loaded(loaded: LoadedClaimsArtifact) -> ModelProvenance:
        """Keep model provenance from an imported typed claim artifact when present."""
        return model_provenance_for_loaded(loaded)
