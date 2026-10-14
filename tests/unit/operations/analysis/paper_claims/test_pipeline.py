import json
import logging
from pathlib import Path

import pytest
from reportlab.pdfgen.canvas import Canvas

from osa_tool.operations.analysis.artifacts import ModelProvenance
from osa_tool.operations.analysis.paper_claims import (
    export_section_extraction,
    extract_claims_from_sections,
    load_sections_json,
)
from osa_tool.operations.analysis.paper_claims.models import (
    ClaimExtractionResult,
    DedupSelection,
    ConvertedChunk,
    ConvertedDocument,
    ExtractedClaim,
    ExtractionMetadata,
    HeadingMeta,
    PaperSection,
    PipelineOptions,
)
from osa_tool.operations.analysis.paper_claims.pipeline import PaperClaimPipeline
from osa_tool.utils.prompts_builder import PromptLoader


class FakeHandler:
    model_settings = type("Settings", (), {"model": "fake-model"})()

    def __init__(self):
        self.successful_models = ["stale-model"]
        self.last_successful_model = "stale-model"
        self.provenance_reset_count = 0
        self.prompts: list[str] = []
        self.system_messages: list[str | None] = []
        self.responses = iter(
            [
                '[{"section_id":"s001"}]',
                "[]",
            ]
        )

    def reset_model_provenance(self):
        self.provenance_reset_count += 1
        self.successful_models.clear()
        self.last_successful_model = None

    async def async_request(self, prompt, system_message=None, retry_delay=1):
        self.prompts.append(prompt)
        self.system_messages.append(system_message)
        self.last_successful_model = self.model_settings.model
        if self.last_successful_model not in self.successful_models:
            self.successful_models.append(self.last_successful_model)
        return next(self.responses)


class FakeConverter:
    def __init__(self):
        self.chunk_paths: list[Path] = []
        self.show_progress: bool | None = None

    def convert(self, chunks, options, *, show_progress=True):
        self.chunk_paths = [item.path for item in chunks]
        self.show_progress = show_progress
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
    assert result.extraction.meta.models_used == ["fake-model"]
    assert result.extraction.meta.configured_model == "fake-model"
    assert converter.chunk_paths
    assert all(not path.exists() for path in converter.chunk_paths)
    assert "Stage 1/4: starting PDF splitting" in caplog.text
    assert "final_claims=0" in caplog.text
    assert converter.show_progress is True

    default_path = PaperClaimPipeline.export(result, tmp_path / "export-default", legacy=True)
    default_payload = json.loads(default_path.read_text())
    assert "debug" not in default_payload
    report_payload = json.loads((tmp_path / "export-default" / "report.json").read_text())
    assert report_payload["meta"] == {
        "source": {"paper": {"kind": "pdf", "path": str(pdf)}},
        "model": {"configured": "fake-model", "used": ["fake-model"]},
    }
    assert report_payload["result"]["meta"]["models_used"] == ["fake-model"]

    debug_path = PaperClaimPipeline.export(result, tmp_path / "export-debug", legacy=True, include_debug=True)
    debug_payload = json.loads(debug_path.read_text())
    assert debug_payload["debug"]["step3_selection"] == []


@pytest.mark.asyncio
async def test_pipeline_clears_stale_provenance_when_a_document_needs_no_model_calls(tmp_path, monkeypatch):
    from osa_tool.operations.analysis.paper_claims import section_extractor

    first_pdf = tmp_path / "first.pdf"
    second_pdf = tmp_path / "second.pdf"
    create_pdf(first_pdf)
    create_pdf(second_pdf)
    handler = FakeHandler()
    pipeline = PaperClaimPipeline(handler, converter=FakeConverter())

    first_result = await pipeline.arun(first_pdf, PipelineOptions())

    async def no_model_calls(_extractor, _sections, *, source=None, model=None):
        return ClaimExtractionResult(
            claims=[],
            deduplication=[],
            selected_section_ids=[],
            meta=ExtractionMetadata(source=source, model=None),
        )

    monkeypatch.setattr(section_extractor.ClaimExtractor, "extract", no_model_calls)

    result = await pipeline.arun(second_pdf, PipelineOptions())

    assert handler.provenance_reset_count == 2
    assert first_result.extraction.meta.models_used == ["fake-model"]
    assert handler.successful_models == []
    assert handler.last_successful_model is None
    assert result.extraction.meta.configured_model == "fake-model"
    assert result.extraction.meta.models_used == []
    assert result.extraction.meta.model is None


@pytest.mark.asyncio
async def test_pipeline_can_disable_nested_progress(tmp_path, monkeypatch):
    from osa_tool.operations.analysis.paper_claims import claim_extractor, claim_deduplicator, pdf_splitter

    pdf = tmp_path / "paper.pdf"
    create_pdf(pdf)
    converter = FakeConverter()

    def progress_must_not_render(*_args, **_kwargs):
        raise AssertionError("nested Rich progress must be disabled")

    monkeypatch.setattr(pdf_splitter, "track", progress_must_not_render)
    monkeypatch.setattr(claim_extractor, "track", progress_must_not_render)
    monkeypatch.setattr(claim_deduplicator, "track", progress_must_not_render)

    await PaperClaimPipeline(FakeHandler(), converter=converter).arun(
        pdf,
        PipelineOptions(),
        show_progress=False,
    )

    assert converter.show_progress is False


@pytest.mark.parametrize(
    ("payload", "source_format"),
    [
        ({"claims": [{"claim": "typed"}], "meta": {"model": "typed-model"}}, "typed"),
        ({"result": [{"claim": "legacy"}], "meta": {"model": "legacy-model"}}, "legacy"),
        ([{"claim": "bare"}], "bare"),
    ],
)
def test_loaded_claims_are_normalized_and_exported_with_provenance(tmp_path, payload, source_format):
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    loaded = PaperClaimPipeline.load_claims_json(input_path)
    claims_path = PaperClaimPipeline.export_loaded_claims(loaded, tmp_path / "output")

    assert loaded.source_format == source_format
    normalized = json.loads(claims_path.read_text(encoding="utf-8"))
    assert normalized["claims"] == loaded.claims
    assert normalized["meta"]["imported"] is True
    report = json.loads((tmp_path / "output" / "report.json").read_text(encoding="utf-8"))
    assert report["meta"]["source"]["paper"] == {"kind": "claims_json", "path": str(input_path)}
    assert report["result"] == normalized


def _section() -> PaperSection:
    return PaperSection(
        section_id="s001",
        name="Method",
        text="The model uses BERT-base.",
        heading_meta=HeadingMeta(raw="2. Method", level=1, numbering="2"),
    )


def _extraction() -> ClaimExtractionResult:
    return ClaimExtractionResult(
        claims=[
            ExtractedClaim(
                claim_id="c0001",
                claim="The model uses BERT-base.",
                original_text="The model uses BERT-base.",
                category="model_architecture",
                value="BERT-base",
                verifiability="high",
                section_id="s001",
                section_name="Method",
                section_heading_raw="2. Method",
            )
        ],
        deduplication=[
            DedupSelection(
                claim_id="c0001",
                claim="The model uses BERT-base.",
                contradiction=False,
            )
        ],
        selected_section_ids=["s001"],
        meta=ExtractionMetadata(
            source="sections.json",
            model="fake-model",
            configured_model="fake-model",
            models_used=["fake-model"],
            filtered_claims=1,
            step3_input_count=1,
            step3_output_count=1,
        ),
    )


@pytest.mark.parametrize(
    ("payload", "source_format"),
    [
        (lambda section: [section.model_dump(mode="json")], "bare"),
        (lambda section: {"sections": [section.model_dump(mode="json")], "meta": {"producer": "fixture"}}, "envelope"),
    ],
)
def test_sections_json_are_loaded_from_bare_list_or_envelope(tmp_path, payload, source_format):
    input_path = tmp_path / "sections.json"
    input_path.write_text(json.dumps(payload(_section()), ensure_ascii=False), encoding="utf-8")

    loaded = load_sections_json(input_path)

    assert loaded.source_format == source_format
    assert loaded.sections == [_section()]
    if source_format == "envelope":
        assert loaded.upstream_meta == {"producer": "fixture"}


def test_sections_json_schema_errors_are_clear(tmp_path):
    input_path = tmp_path / "sections.json"
    input_path.write_text(json.dumps({"sections": [{"section_id": "s001"}]}), encoding="utf-8")

    with pytest.raises(ValueError, match="PaperSection schema"):
        load_sections_json(input_path)


def test_section_extraction_export_writes_claims_sections_and_report(tmp_path):
    claims_path = export_section_extraction(
        _extraction(),
        [_section()],
        tmp_path / "output",
        source_kind="sections_json",
        source_path=tmp_path / "sections.json",
        model=ModelProvenance(configured="fake-model", used=["fake-model"]),
        upstream_meta={"producer": "fixture"},
    )

    assert claims_path == tmp_path / "output" / "claims.json"
    assert claims_path.is_file()
    assert (tmp_path / "output" / "sections.json").is_file()
    report = json.loads((tmp_path / "output" / "report.json").read_text(encoding="utf-8"))
    assert report["meta"]["source"]["paper"] == {
        "kind": "sections_json",
        "path": str(tmp_path / "sections.json"),
    }
    assert report["meta"]["source"]["upstream"] == {"producer": "fixture"}
    assert report["result"]["claims"][0]["claim"] == "The model uses BERT-base."


@pytest.mark.asyncio
async def test_extract_claims_from_sections_uses_prompt_overrides(tmp_path):
    override_dir = tmp_path / "prompts"
    override_dir.mkdir()
    (override_dir / "paper_claims.toml").write_text(
        '[prompts]\nsection_filter_system = "custom section filter system"\n',
        encoding="utf-8",
    )
    handler = FakeHandler()

    result = await extract_claims_from_sections(
        handler,
        [_section()],
        PipelineOptions(),
        prompts=PromptLoader(override_dirs=[override_dir]),
        show_progress=False,
    )

    assert result.selected_section_ids == ["s001"]
    assert handler.system_messages[0] == "custom section filter system"
    assert handler.provenance_reset_count == 1
