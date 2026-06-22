from __future__ import annotations

import asyncio
import json
from pathlib import Path

from osa_tool.operations.analysis.paper_claims.claim_extractor import AsyncModelHandler, ClaimExtractor
from osa_tool.operations.analysis.paper_claims.marker_converter import MarkerDocumentConverter
from osa_tool.operations.analysis.paper_claims.models import PipelineOptions, PipelineResult
from osa_tool.operations.analysis.paper_claims.pdf_splitter import PdfChunker
from osa_tool.operations.analysis.paper_claims.section_parser import MarkdownSectionParser
from osa_tool.utils.logger import logger


class PaperClaimPipeline:
    def __init__(
        self,
        handler: AsyncModelHandler,
        *,
        converter: MarkerDocumentConverter | None = None,
        section_parser: MarkdownSectionParser | None = None,
    ) -> None:
        self.handler = handler
        self.converter = converter or MarkerDocumentConverter()
        self.section_parser = section_parser or MarkdownSectionParser()

    async def arun(self, pdf_path: Path, options: PipelineOptions | None = None) -> PipelineResult:
        options = options or PipelineOptions()
        pdf_path = Path(pdf_path)
        logger.info("Paper claims pipeline started for %s", pdf_path)
        logger.info("Stage 1/4: starting PDF splitting")
        with PdfChunker() as chunker:
            chunks = chunker.split(pdf_path, pages_per_chunk=options.pages_per_chunk)
            logger.info("Stage 1/4 completed: PDF split into %s chunks", len(chunks))
            logger.info("Stage 2/4: starting Marker conversion")
            converted = self.converter.convert(chunks, options.marker)
            logger.info(
                "Stage 2/4 completed: Marker conversion finished (cache_hit=%s)",
                converted.cache_hit,
            )
        logger.info("Stage 3/4: parsing converted Markdown into sections")
        sections = self.section_parser.parse(converted.markdown)
        logger.info("Stage 3/4 completed: parsed %s sections", len(sections))
        model_settings = getattr(self.handler, "model_settings", None)
        model_name = getattr(model_settings, "model", None)
        logger.info("Stage 4/4: starting claim extraction with model %s", model_name or "unknown")
        extraction = await ClaimExtractor(self.handler, max_retries=options.max_retries).extract(
            sections, source=str(converted.source_path), model=model_name
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

    def run(self, pdf_path: Path, options: PipelineOptions | None = None) -> PipelineResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(self.arun(pdf_path, options))
        raise RuntimeError("PaperClaimPipeline.run() cannot be used inside an active event loop; await arun() instead")

    @staticmethod
    def export(result: PipelineResult, output_dir: Path, *, legacy: bool = False) -> Path:
        destination = Path(output_dir)
        logger.info("Exporting paper claims artifacts to %s", destination)
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "document.md").write_text(result.converted_document.markdown, encoding="utf-8")
        (destination / "sections.json").write_text(
            json.dumps([item.model_dump(mode="json") for item in result.sections], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        payload = result.to_legacy_dict() if legacy else result.extraction.model_dump(mode="json")
        output_path = destination / ("claims_legacy.json" if legacy else "claims.json")
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info("Paper claims export completed: %s", output_path)
        return output_path
