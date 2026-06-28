import json

from osa_tool.tools.paper_claims.batch import build_parser, collect_pdf_inputs
from osa_tool.tools.paper_claims.evaluate import compute_semantic_matching, load_claims


def test_collect_pdf_inputs_deduplicates_and_reports_invalid(tmp_path):
    pdf = tmp_path / "paper.pdf"
    pdf.write_bytes(b"%PDF-test")
    text = tmp_path / "notes.txt"
    text.write_text("no")

    paths, failures = collect_pdf_inputs([tmp_path, pdf, text])

    assert paths == [pdf.resolve()]
    assert len(failures) == 1


def test_batch_keeps_gpt_5_4_mini_as_default_model():
    args = build_parser().parse_args(["paper.pdf"])

    assert args.model == "openai/gpt-5.4-mini"


def test_batch_uses_marker_process_isolation_by_default():
    args = build_parser().parse_args(["paper.pdf"])

    assert args.marker_process_isolation is True
    assert args.marker_low_vram is False
    assert args.marker_log_cuda_memory is True
    assert args.include_debug is False


def test_batch_can_disable_marker_process_isolation():
    args = build_parser().parse_args(["paper.pdf", "--no-marker-process-isolation"])

    assert args.marker_process_isolation is False


def test_force_marker_refresh_has_help_text():
    help_text = build_parser().format_help()

    assert "--force-marker-refresh" in help_text
    assert "Ignore existing cached Marker Markdown" in help_text


def test_batch_can_include_debug_payload():
    args = build_parser().parse_args(["paper.pdf", "--include-debug"])

    assert args.include_debug is True


def test_load_claims_accepts_clean_schema(tmp_path):
    llm = tmp_path / "llm.json"
    human = tmp_path / "human.json"
    llm.write_text(json.dumps({"claims": [{"original_text": "Claim A"}]}))
    human.write_text(json.dumps({"claims": ["Claim A"]}))

    assert load_claims(llm, human) == (["Claim A"], ["Claim A"])


def test_empty_semantic_matching_does_not_load_optional_dependencies():
    metrics = compute_semantic_matching([], ["human"])

    assert metrics["num_matched"] == 0
    assert metrics["matching"] == "many_to_one"
