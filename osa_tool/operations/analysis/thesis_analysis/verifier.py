"""Verify typed paper claims against an already-cloned repository."""

from __future__ import annotations

import json
import re
from functools import partial
from pathlib import Path
from typing import Any, Callable

from osa_tool.config.settings import ThesisVerificationSettings
from osa_tool.operations.analysis.artifacts import StageReportMetadata, model_provenance, write_stage_report
from osa_tool.utils.prompts_builder import PromptLoader
from osa_tool.utils.response_cleaner import JsonProcessor
from osa_tool.utils.utils import read_file

from .data_context import CsvAnalyzer
from .models import ClaimSelection, ClaimVerificationResult, ClaimVerificationStats

Progress = Callable[[str, float], None] | None


class ClaimVerifier:
    """Run the OSA.Edu verification policy on an OSA local clone."""

    _HIGH_MEDIUM = frozenset({"high", "medium"})
    _CSV_PATTERN = re.compile(r"\.(csv|tsv)$", re.IGNORECASE)
    _CANDIDATE_PATTERNS = [
        r"(^|/)train[^/]*\.(py|ipynb)$",
        r"(^|/)main\.(py|ipynb)$",
        r"(^|/)run[^/]*\.(py|ipynb)$",
        r"(^|/)model[^/]*\.(py|ipynb)$",
        r"(^|/)experiment[^/]*\.(py|ipynb)$",
        r"(^|/)configs?[^/]*\.(py|yaml|yml|json)$",
        r"(^|/)configs?/.*\.(yaml|yml|json)$",
        r"(^|/)dataset[^/]*\.(py|ipynb)$",
        r"(^|/)data[^/]*\.(py|ipynb)$",
        r"(^|/)solver[^/]*\.(py|ipynb)$",
        r"(^|/)trainer[^/]*\.(py|ipynb)$",
    ]
    _NOTEBOOK_PATTERN = re.compile(r"\.ipynb$", re.IGNORECASE)

    def __init__(
        self,
        clone_dir: str | Path,
        model_handler: Any,
        settings: ThesisVerificationSettings | None = None,
        *,
        prompts: PromptLoader | None = None,
    ) -> None:
        self._clone_dir = Path(clone_dir).resolve()
        self._model_handler = model_handler
        configured_model = getattr(getattr(model_handler, "model_settings", None), "model", None)
        self._configured_model = configured_model if isinstance(configured_model, str) else None
        self._settings = settings or ThesisVerificationSettings()
        self._prompts = prompts or PromptLoader()

    def verify(
        self,
        claims: list[dict[str, Any]],
        flat_paths: list[str],
        *,
        only_high_medium_verifiability: bool = True,
        hide_low_confidence: bool = True,
        on_progress: Progress = None,
    ) -> ClaimVerificationResult:
        """Verify claims in strict, output-safe batches and return reportable results."""
        source_total = len(claims)
        eligible, excluded_low, excluded_invalid = self._eligible_claims(claims, only_high_medium_verifiability)
        selection = ClaimSelection(
            only_high_medium_verifiability=only_high_medium_verifiability,
            allowed_verifiability=sorted(self._HIGH_MEDIUM) if only_high_medium_verifiability else None,
            hide_low_confidence=hide_low_confidence,
        )
        if not eligible:
            return self._result([], selection, source_total, excluded_low, excluded_invalid, csv_stats=[])

        self._progress(on_progress, "Identifying candidate source files...", 0.0)
        snippets = self._read_candidate_code(flat_paths, on_progress)
        csv_section, csv_stats = self._csv_context(eligible, flat_paths, on_progress)
        annotated = self._verify_batches(eligible, flat_paths, snippets, csv_section, on_progress)

        if hide_low_confidence:
            reportable = [claim for claim in annotated if not self._is_low_confidence(claim)]
        else:
            reportable = annotated
        self._progress(on_progress, "Claim verification complete.", 1.0)
        return self._result(
            reportable,
            selection,
            source_total,
            excluded_low,
            excluded_invalid,
            scored_total=len(annotated),
            csv_stats=csv_stats,
        )

    def export(
        self,
        result: ClaimVerificationResult,
        output_dir: str | Path,
        *,
        source: dict[str, Any],
    ) -> Path:
        """Write the canonical verification report with both input sources."""
        if "repository" not in source or "paper" not in source:
            raise ValueError("Claim verification report source must include both 'repository' and 'paper'")
        return write_stage_report(
            Path(output_dir),
            meta=StageReportMetadata(
                source=source,
                model=self.get_model_provenance(),
            ),
            result=result.model_dump(mode="json"),
        )

    def get_model_provenance(self):
        """Return model provenance for the most recent verification run."""
        return model_provenance(self._model_handler, configured=self._configured_model)

    @classmethod
    def _normalized_verifiability(cls, claim: dict[str, Any]) -> str:
        value = claim.get("verifiability")
        return value.strip().lower() if isinstance(value, str) else ""

    @classmethod
    def _eligible_claims(
        cls, claims: list[dict[str, Any]], only_high_medium: bool
    ) -> tuple[list[dict[str, Any]], int, int]:
        if not only_high_medium:
            return list(claims), 0, 0
        eligible: list[dict[str, Any]] = []
        excluded_low = excluded_invalid = 0
        for claim in claims:
            verifiability = cls._normalized_verifiability(claim)
            if verifiability in cls._HIGH_MEDIUM:
                eligible.append(claim)
            elif verifiability == "low":
                excluded_low += 1
            else:
                excluded_invalid += 1
        return eligible, excluded_low, excluded_invalid

    @staticmethod
    def _is_low_confidence(claim: dict[str, Any]) -> bool:
        implementation = claim.get("implementation")
        confidence = implementation.get("confidence") if isinstance(implementation, dict) else None
        return not isinstance(confidence, str) or confidence.strip().lower() == "low"

    def _result(
        self,
        claims: list[dict[str, Any]],
        selection: ClaimSelection,
        source_total: int,
        excluded_low: int,
        excluded_invalid: int,
        *,
        scored_total: int | None = None,
        csv_stats: list[dict[str, Any]],
    ) -> ClaimVerificationResult:
        scored_total = len(claims) if scored_total is None else scored_total
        implemented = sum(1 for claim in claims if bool(claim.get("implementation", {}).get("implemented")))
        total = len(claims)
        return ClaimVerificationResult(
            claims=claims,
            selection=selection,
            stats=ClaimVerificationStats(
                source_total=source_total,
                eligible_total=scored_total,
                scored_total=scored_total,
                excluded_low_verifiability=excluded_low,
                excluded_invalid_verifiability=excluded_invalid,
                hidden_low_confidence=scored_total - total,
                total=total,
                implemented=implemented,
                not_implemented=total - implemented,
                implementation_rate=round(implemented / total, 3) if total else 0.0,
                implementation_rate_pct=round(implemented / total * 100) if total else 0,
            ),
            csv_stats=csv_stats,
        )

    def _read_candidate_code(self, flat_paths: list[str], on_progress: Progress) -> list[str]:
        candidates = self._candidate_files(flat_paths, max_files=self._settings.candidate_file_limit)
        snippets: list[str] = []
        for index, path in enumerate(candidates, start=1):
            try:
                content = self._read_repo_file(path)
                snippet = f"### {path}\n{self._truncate(content, self._settings.source_snippet_max_lines)}"
            except OSError as exc:
                snippet = f"### {path}\n[could not read: {exc}]"
            snippets.append(snippet)
            self._progress(on_progress, f"Read {path}", 0.1 + 0.3 * index / max(len(candidates), 1))
        return snippets

    def _csv_context(
        self, claims: list[dict[str, Any]], flat_paths: list[str], on_progress: Progress
    ) -> tuple[str, list[dict[str, Any]]]:
        if not any(claim.get("category") in {"dataset", "data_preprocessing"} for claim in claims):
            return "", []
        self._progress(on_progress, "Analysing data files (CSV/TSV)...", 0.35)
        stats: list[dict[str, Any]] = []
        csv_paths = [path for path in flat_paths if self._CSV_PATTERN.search(path)][: self._settings.csv_file_limit]
        for index, path in enumerate(csv_paths, start=1):
            try:
                stats.append(CsvAnalyzer(self._read_repo_file(path), filename=path).analyze())
            except OSError as exc:
                stats.append(
                    {
                        "filename": path,
                        "row_count": 0,
                        "column_count": 0,
                        "columns": [],
                        "column_stats": {},
                        "error": str(exc),
                    }
                )
            self._progress(on_progress, f"Analysed {path}", 0.35 + 0.05 * index / max(len(csv_paths), 1))
        if not stats:
            return "", []
        return "## Data file statistics\n" + "\n\n".join(CsvAnalyzer.format_for_prompt(item) for item in stats), stats

    def _verify_batches(
        self,
        claims: list[dict[str, Any]],
        flat_paths: list[str],
        snippets: list[str],
        csv_section: str,
        on_progress: Progress,
    ) -> list[dict[str, Any]]:
        indexed_claims = [
            {
                "index": index,
                "claim": claim.get("claim", ""),
                "category": claim.get("category", ""),
                "value": claim.get("value"),
                "verifiability": claim.get("verifiability", ""),
            }
            for index, claim in enumerate(claims)
        ]
        context = self._verification_context(
            flat_paths,
            snippets,
            csv_section,
            tree_max_paths=self._settings.repository_tree_max_paths,
        )
        batch_starts = list(range(0, len(indexed_claims), self._settings.batch_size))
        verification_by_index: dict[int, dict[str, Any]] = {}
        for batch_number, start in enumerate(batch_starts, start=1):
            batch = indexed_claims[start : start + self._settings.batch_size]
            expected_indices = {item["index"] for item in batch}
            expected_list = sorted(expected_indices)
            prompt = (
                f"## Claims\n{json.dumps(batch, ensure_ascii=False, indent=2)}\n\n{context}"
                "## Response contract\n"
                f"Return exactly {len(batch)} objects for indices {expected_list}. "
                "Include every listed index exactly once; do not add indices from another batch. "
                "Return the JSON array only."
            )
            self._progress(
                on_progress,
                f"Verifying batch {batch_number}/{len(batch_starts)}: claims {start + 1}-{start + len(batch)} of {len(claims)}.",
                0.4 + 0.5 * (batch_number - 1) / len(batch_starts),
            )
            parsed = self._model_handler.send_and_parse(
                prompt,
                partial(self._parse_verification_batch, expected_indices=expected_indices),
                self._prompts.get("thesis_analysis.verify_system"),
            )
            verification_by_index.update({item["index"]: item for item in parsed})

        return [
            {
                **claim,
                "implementation": {
                    "implemented": verification_by_index[index]["implemented"],
                    "confidence": verification_by_index[index].get("confidence", "low"),
                    "evidence_file": verification_by_index[index].get("evidence_file"),
                    "explanation": verification_by_index[index].get("explanation", ""),
                },
            }
            for index, claim in enumerate(claims)
        ]

    @staticmethod
    def _parse_verification_batch(raw: str, expected_indices: set[int]) -> list[dict[str, Any]]:
        parsed = JsonProcessor.parse(raw, expected_type=list)
        indices: list[int] = []
        for item in parsed:
            if not isinstance(item, dict) or type(item.get("index")) is not int:
                raise ValueError("Each verification result must include an integer index")
            if type(item.get("implemented")) is not bool:
                raise ValueError("Each verification result must include a boolean implemented field")
            indices.append(item["index"])
        returned_indices = set(indices)
        if len(indices) != len(returned_indices):
            raise ValueError("Verification response contains duplicate claim indices")
        if returned_indices != expected_indices:
            missing = sorted(expected_indices - returned_indices)
            unexpected = sorted(returned_indices - expected_indices)
            raise ValueError(
                "Verification response does not cover the requested claim indices: "
                f"missing={missing[:10]}, unexpected={unexpected[:10]}"
            )
        return parsed

    def _read_repo_file(self, relative_path: str) -> str:
        path = (self._clone_dir / relative_path).resolve()
        if not path.is_relative_to(self._clone_dir):
            raise OSError(f"Refusing to read outside repository: {relative_path}")
        content = read_file(str(path))
        if not content and self._NOTEBOOK_PATTERN.search(relative_path):
            return "[notebook contained no readable code or markdown cells]"
        return content

    @classmethod
    def _candidate_files(cls, flat_paths: list[str], max_files: int = 6) -> list[str]:
        result: list[str] = []
        for pattern in cls._CANDIDATE_PATTERNS:
            for path in flat_paths:
                if path not in result and re.search(pattern, path, re.IGNORECASE):
                    result.append(path)
                    if len(result) == max_files:
                        return result
        for path in flat_paths:
            if path not in result and cls._NOTEBOOK_PATTERN.search(path):
                result.append(path)
                if len(result) == max_files:
                    return result
        return result

    @staticmethod
    def _truncate(text: str, max_lines: int = 250) -> str:
        lines = text.splitlines()
        if len(lines) <= max_lines:
            return text
        return "\n".join(lines[:max_lines]) + f"\n... (truncated, {len(lines)} total lines)"

    @staticmethod
    def _verification_context(
        flat_paths: list[str],
        snippets: list[str],
        csv_section: str,
        *,
        tree_max_paths: int = 300,
    ) -> str:
        code_context = "\n\n".join(snippets) if snippets else "(no source files selected)"
        tree_sample = "\n".join(flat_paths[:tree_max_paths])
        context = f"## Repository file tree\n{tree_sample}\n\n" f"## Source code\n{code_context}\n\n"
        return context + (csv_section + "\n\n" if csv_section else "")

    @staticmethod
    def _progress(callback: Progress, message: str, percent: float) -> None:
        if callback:
            callback(message, min(percent, 1.0))
