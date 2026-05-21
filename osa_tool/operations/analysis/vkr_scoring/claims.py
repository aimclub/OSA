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

_CANDIDATE_PATTERNS = [
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

Progress = Optional[Callable[[str, float], None]]


def _parse_json_list(raw: str) -> list:
    """Parse raw LLM output as a JSON array via OSA's JsonProcessor."""
    return JsonProcessor.parse(raw, expected_type=list)


def _candidate_files(flat_paths: list[str], max_files: int = 6) -> list[str]:
    found: list[str] = []
    for pat in _CANDIDATE_PATTERNS:
        for path in flat_paths:
            if path not in found and re.search(pat, path, re.IGNORECASE):
                found.append(path)
                if len(found) >= max_files:
                    return found
    return found


def _truncate(text: str, max_lines: int = 250) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text
    return "\n".join(lines[:max_lines]) + f"\n... (truncated, {len(lines)} total lines)"


class ClaimsPipeline:
    """
    Extracts and verifies verifiable claims from a paper against a repository.

    Usage
    -----
    pipeline = ClaimsPipeline(config)
    claims   = pipeline.extract(paper_sections)
    result   = pipeline.verify(claims, flat_paths)
    """

    def __init__(self, config: VkrConfig) -> None:
        self._config = config

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

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

        # Step 1: filter sections
        _prog("Filtering relevant sections...", 0.0)
        section_names = [s["name"] for s in paper_sections]
        retained_names: list[str] = self._config.model_handler.send_and_parse(
            (
                "Below is the list of section headings extracted from the target paper:\n"
                f"{json.dumps(section_names, ensure_ascii=False)}\n"
                "Filter the list and return ONLY a JSON array of the retained section names."
            ),
            _parse_json_list,
            _PROMPTS.get("vkr_scoring.filter_system"),
        )
        _prog(f"Retained {len(retained_names)} sections for claim extraction.", 0.15)

        # Step 2: extract claims per section
        all_raw_claims: list[str] = []
        section_map = {s["name"]: s.get("text", "") for s in paper_sections}

        for i, name in enumerate(retained_names):
            text = section_map.get(name, "")
            if not text.strip():
                continue
            _prog(
                f"Extracting claims from '{name}'...",
                0.15 + 0.50 * (i / max(len(retained_names), 1)),
            )
            claims_list: list = self._config.model_handler.send_and_parse(
                (
                    f"Analyze the following report section and extract all verifiable factual claims:\n\n"
                    f"{text}\n\nReturn ONLY the JSON array."
                ),
                _parse_json_list,
                _PROMPTS.get("vkr_scoring.extract_system"),
            )
            all_raw_claims.append(json.dumps(claims_list, ensure_ascii=False))

        if not all_raw_claims:
            return []

        # Step 3: deduplicate
        _prog("Deduplicating claims...", 0.70)
        final_claims: list = self._config.model_handler.send_and_parse(
            (
                "Below are claims extracted from all sections. Deduplicate and flag contradictions:\n"
                f"{json.dumps(all_raw_claims, ensure_ascii=False)}\n"
                "Return ONLY the final processed JSON array."
            ),
            _parse_json_list,
            _PROMPTS.get("vkr_scoring.dedup_system"),
        )
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
        candidates = _candidate_files(flat_paths)
        code_snippets: list[str] = []
        for path in candidates:
            content = read_file(os.path.join(self._config.clone_dir, path))
            if content:
                code_snippets.append(f"### {path}\n{_truncate(content)}")
            else:
                code_snippets.append(f"### {path}\n[could not read]")
            _prog(f"Read {path}", 0.1 + 0.3 * (len(code_snippets) / max(len(candidates), 1)))

        has_dataset_claims = any(c.get("category") in ("dataset", "data_preprocessing") for c in claims)
        csv_section = ""
        csv_stats_list: list[dict] = []
        if has_dataset_claims:
            _prog("Analysing data files (CSV/TSV)...", 0.35)

            def _csv_prog(msg: str, pct: float) -> None:
                _prog(msg, 0.35 + pct * 0.05)

            csv_stats_list = self._collect_csv_stats(flat_paths, on_progress=_csv_prog)
            if csv_stats_list:
                csv_blocks = [CsvAnalyzer.format_for_prompt(s) for s in csv_stats_list]
                csv_section = "## Data file statistics\n" + "\n\n".join(csv_blocks)

        _prog("Verifying claims against source code...", 0.4)
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

        verifications: list = self._config.model_handler.send_and_parse(
            user_content,
            _parse_json_list,
            _PROMPTS.get("vkr_scoring.verify_system"),
        )
        _prog("Verification complete.", 1.0)

        ver_by_index = {v.get("index", i): v for i, v in enumerate(verifications)}
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

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _collect_csv_stats(
        self,
        flat_paths: list[str],
        on_progress: Progress = None,
        max_files: int = 5,
    ) -> list[dict]:
        csv_paths = [p for p in flat_paths if _CSV_PATTERN.search(p)][:max_files]
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


# ---------------------------------------------------------------------------
# Backward-compatible module-level wrappers
# ---------------------------------------------------------------------------


def collect_csv_stats(
    flat_paths: list[str],
    clone_dir: str,
    on_progress: Progress = None,
    max_files: int = 5,
) -> list[dict]:
    """Backward-compatible wrapper. Use ``ClaimsPipeline._collect_csv_stats`` directly."""
    from .checks import VkrConfig as _VkrConfig  # local import to avoid circular

    # Minimal config — only clone_dir is needed for file I/O
    class _MinimalConfig:
        def __init__(self, d: str) -> None:
            self.clone_dir = d

    pipeline = ClaimsPipeline(_MinimalConfig(clone_dir))  # type: ignore[arg-type]
    return pipeline._collect_csv_stats(flat_paths, on_progress=on_progress, max_files=max_files)


def extract_claims(
    paper_sections: list[dict],
    config: VkrConfig,
    on_progress: Progress = None,
) -> list[dict]:
    """Backward-compatible wrapper. Use ``ClaimsPipeline`` directly for new code."""
    return ClaimsPipeline(config).extract(paper_sections, on_progress)


def verify_claims(
    claims: list[dict],
    flat_paths: list[str],
    config: VkrConfig,
    on_progress: Progress = None,
) -> dict:
    """Backward-compatible wrapper. Use ``ClaimsPipeline`` directly for new code."""
    return ClaimsPipeline(config).verify(claims, flat_paths, on_progress)
