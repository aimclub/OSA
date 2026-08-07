import pytest

pytest.importorskip("doclayout_yolo", reason="paper_parsing optional dependency group is not installed")

from argparse import Namespace

from osa_tool.tools.paper_parsing.batch import build_options, build_parser, collect_pdf_inputs
from tests.unit.operations.analysis.repository_validation.paper_parsing.fixtures import make_settings


def cli_args(**overrides) -> Namespace:
    defaults = {
        "device": None,
        "conf_threshold": None,
        "max_concurrent": None,
        "downsample_factor": None,
        "save_img": False,
        "render_dpi": None,
        "layout_batch_size": None,
    }
    return Namespace(**{**defaults, **overrides})


def test_collect_pdf_inputs_deduplicates_and_reports_invalid(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-test")
    text = tmp_path / "notes.txt"
    text.write_text("no")

    paths, failures = collect_pdf_inputs([tmp_path, pdf, text])

    assert paths == [pdf.resolve()]
    assert len(failures) == 1


def test_batch_runs_without_a_repository_argument():
    args = build_parser().parse_args(["paper.pdf"])

    assert not hasattr(args, "repository")
    assert args.output_dir.name == "paper_parsing_results"


def test_options_come_from_the_configuration_when_no_flags_are_given():
    settings = make_settings(paper_parser_device="cuda", paper_parser_max_concurrent=3)

    options = build_options(cli_args(), settings)

    assert options.device == "cuda"
    assert options.max_concurrent == 3


def test_cli_flags_override_the_configured_options():
    settings = make_settings(paper_parser_device="cuda", paper_parser_max_concurrent=3)

    options = build_options(cli_args(device="cpu", max_concurrent=1, save_img=True), settings)

    assert options.device == "cpu"
    assert options.max_concurrent == 1
    assert options.save_img is True


def test_invalid_confidence_threshold_is_rejected():
    with pytest.raises(ValueError):
        build_options(cli_args(conf_threshold=1.5), make_settings())


def test_memory_tunables_come_from_the_configuration():
    settings = make_settings(paper_parser_render_dpi=150, paper_parser_layout_batch_size=2)

    options = build_options(cli_args(), settings)

    assert options.render_dpi == 150
    assert options.layout_batch_size == 2


def test_memory_tunables_default_when_the_configuration_is_silent():
    options = build_options(cli_args(), make_settings())

    assert options.render_dpi == 200
    assert options.layout_batch_size == 4


def test_cli_flags_override_the_configured_memory_tunables():
    settings = make_settings(paper_parser_render_dpi=150, paper_parser_layout_batch_size=2)

    options = build_options(cli_args(render_dpi=100, layout_batch_size=1), settings)

    assert options.render_dpi == 100
    assert options.layout_batch_size == 1
