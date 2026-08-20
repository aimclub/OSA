from __future__ import annotations

import json

import pytest

from osa_tool.operations.analysis.thesis_analysis.verifier import ClaimVerifier


class BatchHandler:
    def __init__(self, *, low_confidence_indices: set[int] | None = None) -> None:
        self.calls: list[str] = []
        self.low_confidence_indices = low_confidence_indices or set()

    def send_and_parse(self, prompt, parser, _system):
        self.calls.append(prompt)
        claims = json.loads(prompt.split("## Claims\n", 1)[1].split("\n\n## Repository file tree", 1)[0])
        payload = [
            {
                "index": claim["index"],
                "implemented": True,
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


def test_verifier_uses_two_strict_batches_for_fifty_one_claims(tmp_path):
    handler = BatchHandler()
    claims = [{"claim": f"claim {index}", "verifiability": "high"} for index in range(51)]

    result = ClaimVerifier(tmp_path, handler).verify(claims, [])

    assert len(handler.calls) == 2
    assert result.stats.scored_total == 51
    assert result.stats.total == 51


@pytest.mark.parametrize(
    "payload",
    [
        [{"index": 0}, {"index": 0}],
        [{"index": 1}],
    ],
)
def test_verification_batch_rejects_duplicate_missing_or_unexpected_indices(payload):
    with pytest.raises(ValueError, match="duplicate|does not cover"):
        ClaimVerifier._parse_verification_batch(json.dumps(payload), {0})


def test_verifier_adds_csv_statistics_for_dataset_claims(tmp_path):
    (tmp_path / "dataset.csv").write_text("name,value\na,1\nb,2\n", encoding="utf-8")
    handler = BatchHandler()
    result = ClaimVerifier(tmp_path, handler).verify(
        [{"claim": "Dataset has two rows", "category": "dataset", "verifiability": "high"}],
        ["dataset.csv"],
    )

    assert result.csv_stats[0]["filename"] == "dataset.csv"
    assert "## Data file statistics" in handler.calls[0]
