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
