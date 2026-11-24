import json
import sys
from unittest.mock import AsyncMock, Mock

import pytest

pytest.importorskip("doclayout_yolo", reason="paper_parsing optional dependency group is not installed")

from osa_tool.operations.analysis.repository_validation.paper_parsing import pipeline, run_graph_building
from osa_tool.run import main
from osa_tool.operations.analysis.repository_validation.paper_parsing.structured_parser import StructuredPaperParser
from tests.unit.operations.analysis.repository_validation.paper_parsing.fixtures import make_settings


def test_standalone_construction_needs_no_model_settings(tmp_path):
    parser = StructuredPaperParser(tmp_path / "paper.pdf", vlm_model="vlm", api_key="key")

    assert parser.pipeline.vlm_model == "vlm"
    assert parser.options.device == "cpu"


def test_missing_model_is_reported_before_the_pipeline_runs(tmp_path):
    with pytest.raises(ValueError, match="No vision-language model configured"):
        StructuredPaperParser(tmp_path / "paper.pdf", vlm_model="")


def test_from_model_settings_prefers_vlm_extras(monkeypatch, tmp_path):
    monkeypatch.setenv("CUSTOM_KEY", "from-env")
    settings = make_settings(
        vlm_model="vision-model",
        vlm_base_url="https://vlm.example/v1",
        vlm_api_key_env="CUSTOM_KEY",
        paper_parser_device="cuda",
        paper_parser_max_concurrent=2,
    )

    parser = StructuredPaperParser.from_model_settings(tmp_path / "paper.pdf", settings)

    assert parser.pipeline.vlm_model == "vision-model"
    assert parser.pipeline.vlm_base_url == "https://vlm.example/v1"
    assert parser.pipeline.api_key == "from-env"
    assert parser.options.device == "cuda"
    assert parser.options.max_concurrent == 2


def test_blank_extras_fall_back_to_the_model_settings(tmp_path):
    settings = make_settings(vlm_model="", vlm_base_url="", vlm_api_key="config-key")

    parser = StructuredPaperParser.from_model_settings(tmp_path / "paper.pdf", settings)

    assert parser.pipeline.vlm_model == "text-only-model"
    assert parser.pipeline.vlm_base_url == "https://openrouter.ai/api/v1"
    assert parser.pipeline.api_key == "config-key"


def test_explicit_arguments_win_over_the_configuration(tmp_path):
    settings = make_settings(vlm_model="vision-model", vlm_api_key="config-key")

    parser = StructuredPaperParser.from_model_settings(
        tmp_path / "paper.pdf",
        settings,
        vlm_model="override-model",
        api_key="override-key",
    )

    assert parser.pipeline.vlm_model == "override-model"
    assert parser.pipeline.api_key == "override-key"


def test_options_from_model_settings_ignores_placeholder_values():
    options = StructuredPaperParser.options_from_model_settings(make_settings(paper_parser_device=""))

    assert options.device == "cpu"
    assert options.max_concurrent == 5
    assert options.conf_threshold == pytest.approx(0.15)


def test_parse_paper_cli_exports_a_rebuildable_graph(tmp_path, monkeypatch):
    source = tmp_path / "paper.pdf"
    source.touch()
    config = tmp_path / "paper-parser.toml"
    config.write_text('[llm.for_paper_parsing]\nvlm_model = "vision-test"\n', encoding="utf-8")
    destination = tmp_path / "parsed"

    extractor = Mock()
    extractor.pages = []
    extractor.get_bboxes.return_value = [{"name": "title", "page_num": 1, "image_bytes": "example crop"}]
    monkeypatch.setattr(pipeline, "LayoutExtractor", Mock(return_value=extractor))
    describer = Mock()
    describer.process_all_bboxes_async = AsyncMock(return_value=[{"success": True, "bbox_idx": 0, "result": "{}"}])
    describer.parse_json.return_value = {"text": "Methods", "description": ""}
    describe = Mock(return_value=describer)
    monkeypatch.setattr(pipeline, "ImageDescription", describe)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "osa-tool",
            "--parse-paper",
            str(source),
            "--config-file",
            str(config),
            "--paper-parsing-output-dir",
            str(destination),
        ],
    )
    assert main() == 0
    assert describe.call_args.kwargs["model_name"] == "vision-test"
    extractor.close.assert_called_once_with()
    assert (destination / "document.md").read_text(encoding="utf-8") == "## Methods"

    rebuilt = tmp_path / "rebuilt.json"
    run_graph_building(destination / "report.json", rebuilt)
    assert json.loads(rebuilt.read_text(encoding="utf-8")) == json.loads(
        (destination / "graph.json").read_text(encoding="utf-8")
    )


def test_direct_and_staged_pdf_pipelines_agree(tmp_path, monkeypatch):
    import asyncio
    from reportlab.pdfgen.canvas import Canvas
    from osa_tool.operations.analysis.repository_validation.paper_parsing import doc_layout, doc_ocr

    source = tmp_path / "sample.PDF"
    pdf = Canvas(str(source), pagesize=(150, 150))
    for label in ("Methods", "Results"):
        pdf.drawString(12, 120, label)
        pdf.showPage()
    pdf.save()

    # Mock only the model boundaries. Both runs render and crop actual PDF pages.
    detection = Mock()
    detection.tojson.return_value = json.dumps(
        [{"name": "title", "class": 0, "confidence": 0.99, "box": {"x1": 5, "y1": 5, "x2": 90, "y2": 45}}]
    )
    model = Mock()
    model.predict.side_effect = lambda pages, **kwargs: [detection for _ in pages]
    monkeypatch.setattr(doc_layout, "hf_hub_download", Mock(return_value="weights.pt"))
    monkeypatch.setattr(doc_layout, "YOLOv10", Mock(return_value=Mock(to=Mock(return_value=model))))
    client = Mock()
    reply = Mock()
    reply.choices = [Mock(message=Mock(content='{"text": "Heading", "description": ""}'))]
    client.chat.completions.create = AsyncMock(return_value=reply)
    monkeypatch.setattr(doc_ocr, "AsyncOpenAI", Mock(return_value=client))

    parser = StructuredPaperParser(source, vlm_model="vision")
    direct = parser.parse()
    assert parser.parse_layout(tmp_path / "layout") == 2
    resumed = asyncio.run(parser.adescribe(tmp_path / "layout"))
    assert resumed.requested == resumed.described == 2
    assert resumed.markdown == direct.markdown == "## Heading\n\n## Heading"
    for name, result in (("direct", direct), ("resumed", resumed)):
        parser.export(result, tmp_path / name, include_report=True)
    for filename in ("report.json", "graph.json"):
        assert json.loads((tmp_path / "direct" / filename).read_text()) == json.loads(
            (tmp_path / "resumed" / filename).read_text()
        )


def test_zero_retry_settings_survive_configuration():
    options = StructuredPaperParser.options_from_model_settings(
        make_settings(paper_parser_vlm_max_retries=0, paper_parser_vlm_retry_delay=0)
    )
    assert options.vlm_max_retries == options.vlm_retry_delay == 0


def test_unusable_responses_do_not_discard_successful_elements():
    describer = Mock(parse_json=json.loads)
    report = [{}, {}]
    results = [
        {"success": True, "bbox_idx": 0, "result": "[]"},
        {"success": True, "bbox_idx": 1, "result": '{"text":"Methods"}'},
    ]
    assert pipeline.PaperParsingPipeline._merge_descriptions(report, results, describer) == 1
    with pytest.raises(pipeline.DescriptionError):
        pipeline.PaperParsingPipeline._merge_descriptions(report, results[:1], describer)


def test_graph_preserves_cross_page_references_and_renders_caption_once():
    report = [
        {"name": "title", "text": "Results", "page_num": 0},
        {"name": "plain text", "text": "See Fig. 7.", "page_num": 0},
        {"name": "figure", "description": "Measured values.", "page_num": 1},
        {"name": "figure_caption", "text": "Figure 7. Results.", "page_num": 1, "caption_for": 2},
    ]
    graph = pipeline.build_document_graph(report)
    edges = {(edge["source"], edge["edge_type"], edge["target"]) for edge in graph["edges"]}
    assert ("elem_1", "text_references", "elem_2") in edges
    assert ("elem_3", "caption_of", "elem_2") in edges
    assert ("page_0", "next_page", "page_1") in edges
    markdown = pipeline.PaperParsingPipeline.linearize(graph)
    assert "[Figure] Measured values. Figure 7. Results." in markdown
    assert markdown.count("Figure 7. Results.") == 1
