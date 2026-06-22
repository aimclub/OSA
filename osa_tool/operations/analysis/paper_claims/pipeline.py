from __future__ import annotations

import asyncio
import json
from pathlib import Path

from osa_tool.operations.analysis.paper_claims.claim_extractor import AsyncModelHandler, ClaimExtractor
from osa_tool.operations.analysis.paper_claims.marker_converter import MarkerDocumentConverter
from osa_tool.operations.analysis.paper_claims.models import PipelineOptions, PipelineResult
from osa_tool.operations.analysis.paper_claims.pdf_splitter import PdfChunker
from osa_tool.operations.analysis.paper_claims.section_parser import MarkdownSectionParser


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
        with PdfChunker() as chunker:
            chunks = chunker.split(Path(pdf_path), pages_per_chunk=options.pages_per_chunk)
            converted = self.converter.convert(chunks, options.marker)
        sections = self.section_parser.parse(converted.markdown)
        model_settings = getattr(self.handler, "model_settings", None)
        model_name = getattr(model_settings, "model", None)
        extraction = await ClaimExtractor(self.handler, max_retries=options.max_retries).extract(
            sections, source=str(converted.source_path), model=model_name
        )
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
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "document.md").write_text(result.converted_document.markdown, encoding="utf-8")
        (destination / "sections.json").write_text(
            json.dumps([item.model_dump(mode="json") for item in result.sections], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        payload = result.to_legacy_dict() if legacy else result.extraction.model_dump(mode="json")
        output_path = destination / ("claims_legacy.json" if legacy else "claims.json")
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return output_path
