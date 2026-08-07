import pytest

pytest.importorskip("doclayout_yolo", reason="paper_parsing optional dependency group is not installed")

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
