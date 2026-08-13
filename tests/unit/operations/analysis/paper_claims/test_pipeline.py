import json
import logging
from pathlib import Path

import pytest
from reportlab.pdfgen.canvas import Canvas

from osa_tool.operations.analysis.paper_claims.models import ConvertedChunk, ConvertedDocument, PipelineOptions
from osa_tool.operations.analysis.paper_claims.pipeline import PaperClaimPipeline


class FakeHandler:
    model_settings = type("Settings", (), {"model": "fake-model"})()

    def __init__(self):
        self.responses = iter(
            [
                '[{"section_id":"s001"}]',
                "[]",
            ]
        )

    async def async_request(self, prompt, system_message=None, retry_delay=1):
        return next(self.responses)


class FakeConverter:
    def __init__(self):
        self.chunk_paths: list[Path] = []

    def convert(self, chunks, options):
        self.chunk_paths = [item.path for item in chunks]
        return ConvertedDocument(
            source_path=chunks[0].source_path,
            source_hash=chunks[0].source_hash,
            chunks=[ConvertedChunk(index=1, start_page=1, end_page=1, markdown="# Method\nBody")],
            markdown="# Method\nBody",
        )


def create_pdf(path: Path) -> None:
    canvas = Canvas(str(path))
    canvas.drawString(50, 750, "Page")
    canvas.showPage()
    canvas.save()


@pytest.mark.asyncio
async def test_pipeline_composes_stages_and_removes_pdf_chunks(tmp_path, caplog):
    pdf = tmp_path / "paper.pdf"
    create_pdf(pdf)
    converter = FakeConverter()
    caplog.set_level(logging.INFO, logger="rich")

    result = await PaperClaimPipeline(FakeHandler(), converter=converter).arun(pdf, PipelineOptions())

    assert result.sections[0].name == "Method"
    assert result.extraction.meta.model == "fake-model"
    assert converter.chunk_paths
    assert all(not path.exists() for path in converter.chunk_paths)
    assert "Stage 1/4: starting PDF splitting" in caplog.text
    assert "final_claims=0" in caplog.text

    default_path = PaperClaimPipeline.export(result, tmp_path / "export-default", legacy=True)
    default_payload = json.loads(default_path.read_text())
    assert "debug" not in default_payload

    debug_path = PaperClaimPipeline.export(result, tmp_path / "export-debug", legacy=True, include_debug=True)
    debug_payload = json.loads(debug_path.read_text())
    assert debug_payload["debug"]["step3_selection"] == []
