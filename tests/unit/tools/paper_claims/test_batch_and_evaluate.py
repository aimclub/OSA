import json

import numpy as np
import pytest

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
    assert args.dedup_batch_size == 100


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


def test_batch_can_configure_dedup_batch_size():
    args = build_parser().parse_args(["paper.pdf", "--dedup-batch-size", "25"])
    help_text = build_parser().format_help()

    assert args.dedup_batch_size == 25
    assert "--dedup-batch-size" in help_text
    assert "Maximum number of extracted claims" in help_text
    assert "Minimum: 2" in help_text


def test_batch_rejects_dedup_batch_size_below_two():
    with pytest.raises(SystemExit):
        build_parser().parse_args(["paper.pdf", "--dedup-batch-size", "1"])


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


class FakeEmbeddingModel:
    def __init__(self, embeddings):
        self.embeddings = iter(embeddings)

    def encode(self, *_args, **_kwargs):
        return next(self.embeddings)


def test_many_to_one_recall_counts_unique_human_matches():
    llm = np.array([[1.0, 0.0], [1.0, 0.0], [1.0, 0.0]])
    human = np.array([[1.0, 0.0], [0.0, 1.0]])
    metrics = compute_semantic_matching(["a", "b", "c"], ["x", "y"], model=FakeEmbeddingModel([llm, human]))

    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.6667


def test_one_to_one_prioritizes_number_of_threshold_matches():
    # Directly use unit vectors whose dot products create two valid diagonal
    # edges while the highest-similarity cross edge blocks them under a plain
    # maximum-similarity assignment.
    llm = np.eye(2)
    human = np.array([[1.0, 0.7], [0.8, 0.8]])
    metrics = compute_semantic_matching(
        ["a", "b"],
        ["x", "y"],
        threshold=0.75,
        matching="one_to_one",
        model=FakeEmbeddingModel([llm, human]),
    )

    assert metrics["num_matched"] == 2
