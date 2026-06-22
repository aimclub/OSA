"""
Claim extraction and verification pipeline.

Flow:
  1. Filter paper sections (keep only methodology/results).
  2. Extract verifiable claims per retained section.
  3. Deduplicate / flag contradictions across sections.
  4. Verify each claim against repository source code.

Uses OSA's ModelHandler.send_and_parse() for all LLM calls (retries, JSON
cleaning, and fence stripping are handled there — no duplication needed).
File access goes through the already-cloned local repo.
"""

from __future__ import annotations

import json
import os
import re
import sys
from typing import Callable, Optional

from osa_tool.utils.prompts_builder import PromptLoader
from osa_tool.utils.response_cleaner import JsonProcessor
from osa_tool.utils.utils import read_file

from .checks import VkrConfig
from .csv_analyzer import CsvAnalyzer

_PROMPTS = PromptLoader()

Progress = Optional[Callable[[str, float], None]]


class ClaimsPipeline:
    """
    Extracts and verifies verifiable claims from a paper against a repository.

    Usage
    -----
    pipeline = ClaimsPipeline(config)
    claims   = pipeline.extract(paper_sections)
    result   = pipeline.verify(claims, flat_paths)
    """

    # ── Class-level constants ─────────────────────────────────────────────────

    _CANDIDATE_PATTERNS: list[str] = [
        r"(^|/)train[^/]*\.py$",
        r"(^|/)main\.py$",
        r"(^|/)run[^/]*\.py$",
        r"(^|/)model[^/]*\.py$",
        r"(^|/)experiment[^/]*\.py$",
        r"(^|/)configs?[^/]*\.(py|yaml|yml|json)$",
        r"(^|/)configs?/.*\.(yaml|yml|json)$",
        r"(^|/)dataset[^/]*\.py$",
        r"(^|/)data[^/]*\.py$",
        r"(^|/)solver[^/]*\.py$",
        r"(^|/)trainer[^/]*\.py$",
    ]

    _CSV_PATTERN = re.compile(r"\.(csv|tsv)$", re.IGNORECASE)

    # ── Construction ──────────────────────────────────────────────────────────

    def __init__(self, config: VkrConfig) -> None:
        self._config = config

    # ── Public API ────────────────────────────────────────────────────────────

    def extract(
        self,
        paper_sections: list[dict],
        on_progress: Progress = None,
    ) -> list[dict]:
        """Run the 3-step extraction pipeline. Returns deduplicated claim dicts."""

        def _prog(msg: str, pct: float) -> None:
            print(msg, file=sys.stderr)
            if on_progress:
                on_progress(msg, pct)

        _prog("Filtering relevant sections...", 0.0)
        retained_names = self._filter_sections(paper_sections)
        _prog(f"Retained {len(retained_names)} sections for claim extraction.", 0.15)

        all_raw_claims = self._extract_per_section(retained_names, paper_sections, _prog)

        if not all_raw_claims:
            return []

        _prog("Deduplicating claims...", 0.70)
        final_claims = self._deduplicate_claims(all_raw_claims)
        _prog(f"Extracted {len(final_claims)} unique claims.", 1.0)
        return final_claims

    def verify(
        self,
        claims: list[dict],
        flat_paths: list[str],
        on_progress: Progress = None,
    ) -> dict:
        """Verify each claim against repository source code."""

        def _prog(msg: str, pct: float) -> None:
            print(msg, file=sys.stderr)
            if on_progress:
                on_progress(msg, pct)

        if not claims:
            return {
                "claims": [],
                "stats": {
                    "total": 0,
                    "implemented": 0,
                    "implementation_rate": 0.0,
                    "implementation_rate_pct": 0,
                },
            }

        _prog("Identifying candidate source files...", 0.0)
        code_snippets = self._read_candidate_code(flat_paths, _prog)

        csv_section, csv_stats_list = self._collect_csv_context(claims, flat_paths, _prog)

        _prog("Verifying claims against source code...", 0.4)
        verifications = self._run_verification(claims, flat_paths, code_snippets, csv_section)

        _prog("Verification complete.", 1.0)

        annotated = self._annotate_claims(claims, verifications)
        return self._build_verify_result(annotated, csv_stats_list)

    # ── Private: extract helpers ──────────────────────────────────────────────

    def _filter_sections(self, paper_sections: list[dict]) -> list[str]:
        """Ask the LLM to retain only methodology/results sections."""
        section_names = [s["name"] for s in paper_sections]
        try:
            return self._config.model_handler.send_and_parse(
                (
                    "Below is the list of section headings extracted from the target paper:\n"
                    f"{json.dumps(section_names, ensure_ascii=False)}\n"
                    "Filter the list and return ONLY a JSON array of the retained section names."
                ),
                self._parse_json_list,
                _PROMPTS.get("vkr_scoring.filter_system"),
            )
        except Exception:
            print("Warning: section filter LLM failed; using all sections.", file=sys.stderr)
            return section_names

    def _extract_per_section(
        self,
        retained_names: list[str],
        paper_sections: list[dict],
        _prog: Callable,
    ) -> list[str]:
        """Extract claims from each retained section; return list of JSON strings."""
        section_map = {s["name"]: s.get("text", "") for s in paper_sections}
        all_raw_claims: list[str] = []

        for i, name in enumerate(retained_names):
            text = section_map.get(name, "")
            if not text.strip():
                continue
            _prog(
                f"Extracting claims from '{name}'...",
                0.15 + 0.50 * (i / max(len(retained_names), 1)),
            )
            try:
                claims_list: list = self._config.model_handler.send_and_parse(
                    (
                        f"Analyze the following report section and extract all verifiable factual claims:\n\n"
                        f"{text}\n\nReturn ONLY the JSON array."
                    ),
                    self._parse_json_list,
                    _PROMPTS.get("vkr_scoring.extract_system"),
                )
                all_raw_claims.append(json.dumps(claims_list, ensure_ascii=False))
            except Exception:
                print(f"Warning: failed to extract claims from section '{name}', skipping.", file=sys.stderr)

        return all_raw_claims

    def _deduplicate_claims(self, all_raw_claims: list[str]) -> list[dict]:
        """Merge and deduplicate raw claims from all sections."""
        try:
            return self._config.model_handler.send_and_parse(
                (
                    "Below are claims extracted from all sections. Deduplicate and flag contradictions:\n"
                    f"{json.dumps(all_raw_claims, ensure_ascii=False)}\n"
                    "Return ONLY the final processed JSON array."
                ),
                self._parse_json_list,
                _PROMPTS.get("vkr_scoring.dedup_system"),
            )
        except Exception:
            print("Warning: deduplication LLM failed; merging raw claims without dedup.", file=sys.stderr)
            combined: list[dict] = []
            for raw in all_raw_claims:
                try:
                    combined.extend(json.loads(raw))
                except Exception:
                    pass
            return combined

    # ── Private: verify helpers ───────────────────────────────────────────────

    def _read_candidate_code(
        self,
        flat_paths: list[str],
        _prog: Callable,
    ) -> list[str]:
        """Read the most likely source files and return formatted snippets."""
        candidates = self._candidate_files(flat_paths)
        code_snippets: list[str] = []
        for path in candidates:
            content = read_file(os.path.join(self._config.clone_dir, path))
            snippet = f"### {path}\n{self._truncate(content)}" if content else f"### {path}\n[could not read]"
            code_snippets.append(snippet)
            _prog(f"Read {path}", 0.1 + 0.3 * (len(code_snippets) / max(len(candidates), 1)))
        return code_snippets

    def _collect_csv_context(
        self,
        claims: list[dict],
        flat_paths: list[str],
        _prog: Callable,
    ) -> tuple[str, list[dict]]:
        """Collect CSV statistics when dataset-related claims are present."""
        has_dataset_claims = any(c.get("category") in ("dataset", "data_preprocessing") for c in claims)
        if not has_dataset_claims:
            return "", []

        _prog("Analysing data files (CSV/TSV)...", 0.35)

        def _csv_prog(msg: str, pct: float) -> None:
            _prog(msg, 0.35 + pct * 0.05)

        csv_stats_list = self._collect_csv_stats(flat_paths, on_progress=_csv_prog)
        if not csv_stats_list:
            return "", []

        csv_blocks = [CsvAnalyzer.format_for_prompt(s) for s in csv_stats_list]
        csv_section = "## Data file statistics\n" + "\n\n".join(csv_blocks)
        return csv_section, csv_stats_list

    def _run_verification(
        self,
        claims: list[dict],
        flat_paths: list[str],
        code_snippets: list[str],
        csv_section: str,
    ) -> list:
        """Send claims + code context to the LLM and return raw verification list."""
        claims_for_prompt = [
            {
                "index": i,
                "claim": c.get("claim", ""),
                "category": c.get("category", ""),
                "value": c.get("value"),
                "verifiability": c.get("verifiability", ""),
            }
            for i, c in enumerate(claims)
        ]
        file_tree_sample = "\n".join(flat_paths[:300])
        code_context = "\n\n".join(code_snippets) if code_snippets else "(no source files fetched)"

        user_content = (
            f"## Claims\n{json.dumps(claims_for_prompt, ensure_ascii=False, indent=2)}\n\n"
            f"## Repository file tree\n{file_tree_sample}\n\n"
            f"## Source code\n{code_context}\n\n"
        )
        if csv_section:
            user_content += csv_section + "\n\n"
        user_content += "Return the JSON array."

        return self._config.model_handler.send_and_parse(
            user_content,
            self._parse_json_list,
            _PROMPTS.get("vkr_scoring.verify_system"),
        )

    def _annotate_claims(self, claims: list[dict], verifications: list) -> list[dict]:
        """Merge LLM verification results back onto the original claim objects."""
        ver_by_index = {}
        for i, v in enumerate(verifications):
            idx = v.get("index")
            ver_by_index[i if idx is None else idx] = v
        annotated: list[dict] = []
        for i, claim in enumerate(claims):
            ver = ver_by_index.get(i, {})
            annotated.append(
                {
                    **claim,
                    "implementation": {
                        "implemented": ver.get("implemented", False),
                        "confidence": ver.get("confidence", "low"),
                        "evidence_file": ver.get("evidence_file"),
                        "explanation": ver.get("explanation", ""),
                    },
                }
            )
        return annotated

    def _build_verify_result(self, annotated: list[dict], csv_stats_list: list[dict]) -> dict:
        """Assemble the final verification result dict with stats."""
        implemented = sum(1 for c in annotated if c["implementation"]["implemented"])
        total = len(annotated)
        result: dict = {
            "claims": annotated,
            "stats": {
                "total": total,
                "implemented": implemented,
                "not_implemented": total - implemented,
                "implementation_rate": round(implemented / total, 3) if total else 0.0,
                "implementation_rate_pct": round(implemented / total * 100) if total else 0,
            },
        }
        if csv_stats_list:
            result["csv_stats"] = csv_stats_list
        return result

    # ── Private: CSV stats ────────────────────────────────────────────────────

    def _collect_csv_stats(
        self,
        flat_paths: list[str],
        on_progress: Progress = None,
        max_files: int = 5,
    ) -> list[dict]:
        csv_paths = [p for p in flat_paths if self._CSV_PATTERN.search(p)][:max_files]
        results = []
        for i, path in enumerate(csv_paths):
            if on_progress:
                on_progress(f"Analysing data file {path}...", i / max(len(csv_paths), 1))
            try:
                content = read_file(os.path.join(self._config.clone_dir, path))
                stats = CsvAnalyzer(content, filename=path).analyze()
            except Exception as exc:
                stats = {
                    "filename": path,
                    "row_count": 0,
                    "column_count": 0,
                    "columns": [],
                    "column_stats": {},
                    "error": str(exc),
                }
            results.append(stats)
        return results

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json_list(raw: str) -> list:
        """Parse raw LLM output as a JSON array via OSA's JsonProcessor."""
        return JsonProcessor.parse(raw, expected_type=list)

    @classmethod
    def _candidate_files(cls, flat_paths: list[str], max_files: int = 6) -> list[str]:
        """Return paths most likely to contain model/training/experiment code."""
        found: list[str] = []
        for pat in cls._CANDIDATE_PATTERNS:
            for path in flat_paths:
                if path not in found and re.search(pat, path, re.IGNORECASE):
                    found.append(path)
                    if len(found) >= max_files:
                        return found
        return found

    @staticmethod
    def _truncate(text: str, max_lines: int = 250) -> str:
        """Trim *text* to *max_lines* lines and append a truncation note."""
        lines = text.splitlines()
        if len(lines) <= max_lines:
            return text
        return "\n".join(lines[:max_lines]) + f"\n... (truncated, {len(lines)} total lines)"
