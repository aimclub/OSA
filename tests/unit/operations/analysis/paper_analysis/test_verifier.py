from __future__ import annotations

import json

import pytest

from osa_tool.config.settings import PaperVerificationSettings
from osa_tool.operations.analysis.paper_analysis.verifier import ClaimVerifier


class BatchHandler:
    def __init__(
        self,
        *,
        low_confidence_indices: set[int] | None = None,
        implemented_by_index: dict[int, bool] | None = None,
    ) -> None:
        self.calls: list[str] = []
        self.system_prompts: list[str] = []
        self.low_confidence_indices = low_confidence_indices or set()
        self.implemented_by_index = implemented_by_index or {}

    def send_and_parse(self, prompt, parser, _system):
        self.calls.append(prompt)
        self.system_prompts.append(_system)
        claims = json.loads(prompt.split("## Claims\n", 1)[1].split("\n\n## Repository file tree", 1)[0])
        payload = [
            {
                "index": claim["index"],
                "implemented": self.implemented_by_index.get(claim["index"], True),
                "confidence": "low" if claim["index"] in self.low_confidence_indices else "high",
                "evidence_file": "main.py",
                "explanation": "Evidence found.",
            }
            for claim in claims
        ]
        return parser(json.dumps(payload))


def test_verifier_filters_before_llm_and_hides_low_confidence(tmp_path):
    (tmp_path / "main.py").write_text("optimizer = 'adam'", encoding="utf-8")
    handler = BatchHandler(low_confidence_indices={1})
    claims = [
        {"claim": "first", "verifiability": "high"},
        {"claim": "second", "verifiability": "medium"},
        {"claim": "third", "verifiability": "low"},
        {"claim": "fourth"},
    ]

    result = ClaimVerifier(tmp_path, handler).verify(claims, ["main.py"])

    assert len(handler.calls) == 1
    assert '"claim": "third"' not in handler.calls[0]
    assert result.stats.source_total == 4
    assert result.stats.eligible_total == 2
    assert result.stats.excluded_low_verifiability == 1
    assert result.stats.excluded_invalid_verifiability == 1
    assert result.stats.hidden_low_confidence == 1
    assert result.stats.total == result.stats.implemented == 1
    assert result.stats.implementation_rate_pct == 100
    assert handler.system_prompts[0] == ClaimVerifier(tmp_path, handler)._prompts.get("paper_analysis.verify_system")


def test_verifier_splits_fifty_six_claims_before_the_model_response_limit(tmp_path):
    handler = BatchHandler()
    claims = [{"claim": f"claim {index}", "verifiability": "high"} for index in range(56)]

    result = ClaimVerifier(tmp_path, handler).verify(claims, [])

    assert len(handler.calls) == 3
    batch_sizes = [
        len(json.loads(call.split("## Claims\n", 1)[1].split("\n\n## Repository file tree", 1)[0]))
        for call in handler.calls
    ]
    assert batch_sizes == [25, 25, 6]
    assert "Return exactly 6 objects for indices [50, 51, 52, 53, 54, 55]" in handler.calls[-1]
    assert result.stats.scored_total == 56
    assert result.stats.total == 56


def test_verifier_uses_configured_context_limits_and_batch_size(tmp_path):
    (tmp_path / "main.py").write_text("\n".join(f"line {index}" for index in range(10)), encoding="utf-8")
    handler = BatchHandler()
    settings = PaperVerificationSettings(
        batch_size=2,
        candidate_file_limit=1,
        source_snippet_max_lines=2,
        repository_tree_max_paths=1,
        csv_file_limit=1,
    )

    ClaimVerifier(tmp_path, handler, settings).verify(
        [{"claim": f"claim {index}", "verifiability": "high"} for index in range(3)],
        ["main.py", "ignored.py"],
    )

    assert len(handler.calls) == 2
    assert "line 2" not in handler.calls[0]
    assert "ignored.py" not in handler.calls[0]


@pytest.mark.parametrize(
    "payload",
    [
        [
            {"index": 0, "implemented": True, "confidence": "high"},
            {"index": 0, "implemented": False, "confidence": "low"},
        ],
        [{"index": 1, "implemented": False, "confidence": "medium"}],
    ],
)
def test_verification_batch_rejects_duplicate_missing_or_unexpected_indices(payload):
    with pytest.raises(ValueError, match="duplicate|does not cover"):
        ClaimVerifier._parse_verification_batch(json.dumps(payload), {0})


@pytest.mark.parametrize(
    "payload",
    [
        [{"index": 0, "implemented": "false", "confidence": "high"}],
        [{"index": 0, "implemented": 0, "confidence": "high"}],
        [{"index": 0, "confidence": "high"}],
    ],
)
def test_verification_batch_rejects_non_boolean_implemented_values(payload):
    with pytest.raises(ValueError, match="boolean implemented"):
        ClaimVerifier._parse_verification_batch(json.dumps(payload), {0})


@pytest.mark.parametrize(
    "confidence",
    ["unknown", "uncertain", "HIGH", " medium", None, 1],
)
def test_verification_batch_rejects_unsupported_confidence_values(confidence):
    payload = [{"index": 0, "implemented": True, "confidence": confidence}]

    with pytest.raises(ValueError, match="confidence: high, medium, or low"):
        ClaimVerifier._parse_verification_batch(json.dumps(payload), {0})


def test_verification_batch_rejects_missing_confidence():
    payload = [{"index": 0, "implemented": True}]

    with pytest.raises(ValueError, match="confidence: high, medium, or low"):
        ClaimVerifier._parse_verification_batch(json.dumps(payload), {0})


@pytest.mark.parametrize("confidence", ["high", "medium", "low"])
def test_verification_batch_accepts_canonical_confidence_values(confidence):
    payload = [{"index": 0, "implemented": True, "confidence": confidence}]

    assert ClaimVerifier._parse_verification_batch(json.dumps(payload), {0}) == payload


def test_verifier_preserves_a_valid_false_implementation_value(tmp_path):
    handler = BatchHandler(implemented_by_index={0: False})

    result = ClaimVerifier(tmp_path, handler).verify([{"claim": "missing", "verifiability": "high"}], [])

    assert result.claims[0]["implementation"]["implemented"] is False
    assert result.stats.implemented == 0
    assert result.stats.implementation_rate_pct == 0


def test_verifier_adds_csv_statistics_for_dataset_claims(tmp_path):
    (tmp_path / "dataset.csv").write_text("name,value\na,1\nb,2\n", encoding="utf-8")
    handler = BatchHandler()
    result = ClaimVerifier(tmp_path, handler).verify(
        [{"claim": "Dataset has two rows", "category": "dataset", "verifiability": "high"}],
        ["dataset.csv"],
    )

    assert result.csv_stats[0]["filename"] == "dataset.csv"
    assert "## Data file statistics" in handler.calls[0]


def test_verifier_reads_notebook_context_with_the_existing_reader(tmp_path):
    notebook = tmp_path / "notebooks" / "train.ipynb"
    notebook.parent.mkdir()
    notebook.write_text(
        json.dumps(
            {
                "cells": [
                    {"cell_type": "markdown", "source": ["# Experiment"]},
                    {"cell_type": "code", "source": ["model.fit(features, labels)\n"]},
                ]
            }
        ),
        encoding="utf-8",
    )
    handler = BatchHandler()

    ClaimVerifier(tmp_path, handler).verify(
        [{"claim": "The model is trained", "verifiability": "high"}],
        ["notebooks/train.ipynb"],
    )

    assert "### notebooks/train.ipynb" in handler.calls[0]
    assert "# --- CODE CELL ---" in handler.calls[0]
    assert "model.fit(features, labels)" in handler.calls[0]


def test_candidate_files_include_remaining_notebooks_after_named_sources():
    candidates = ClaimVerifier._candidate_files(
        ["main.py", "notebooks/train.ipynb", "notebooks/exploration.ipynb"],
        max_files=3,
    )

    assert candidates == ["notebooks/train.ipynb", "main.py", "notebooks/exploration.ipynb"]


def test_candidate_files_fall_back_to_ordinary_python_modules(tmp_path):
    module = tmp_path / "src" / "architecture.py"
    module.parent.mkdir()
    module.write_text("class Architecture: pass", encoding="utf-8")
    handler = BatchHandler()

    ClaimVerifier(tmp_path, handler).verify(
        [{"claim": "An architecture is implemented", "verifiability": "high"}],
        ["src/architecture.py"],
    )

    assert ClaimVerifier._candidate_files(["src/architecture.py"]) == ["src/architecture.py"]
    assert "### src/architecture.py" in handler.calls[0]
    assert "class Architecture" in handler.calls[0]


def test_verifier_marks_unreadable_notebook_context(tmp_path):
    notebook = tmp_path / "analysis.ipynb"
    notebook.write_text("{not valid json", encoding="utf-8")
    handler = BatchHandler()

    ClaimVerifier(tmp_path, handler).verify(
        [{"claim": "A notebook analysis exists", "verifiability": "high"}],
        ["analysis.ipynb"],
    )

    assert "[notebook contained no readable code or markdown cells]" in handler.calls[0]


def test_verifier_exports_a_report_with_both_sources(tmp_path):
    handler = BatchHandler()
    verifier = ClaimVerifier(tmp_path, handler)
    result = verifier.verify([{"claim": "implemented", "verifiability": "high"}], [])

    report_path = verifier.export(
        result,
        tmp_path / "claim_verification",
        source={
            "repository": "https://github.com/example/repository",
            "paper": {"kind": "pdf", "path": "/tmp/paper.pdf"},
        },
    )

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["meta"] == {
        "source": {
            "repository": "https://github.com/example/repository",
            "paper": {"kind": "pdf", "path": "/tmp/paper.pdf"},
        },
        "model": {"configured": None, "used": []},
    }
    assert payload["result"] == result.model_dump(mode="json")


def test_verifier_export_requires_repository_and_paper_sources(tmp_path):
    verifier = ClaimVerifier(tmp_path, BatchHandler())
    result = verifier.verify([], [])

    with pytest.raises(ValueError, match="both 'repository' and 'paper'"):
        verifier.export(result, tmp_path / "output", source={"repository": "repo"})
