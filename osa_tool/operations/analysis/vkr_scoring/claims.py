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
from typing import Any, Callable, Optional

from osa_tool.utils.response_cleaner import JsonParseError, JsonProcessor

from .checks import VkrConfig
from .csv_analyzer import analyze_csv, format_csv_stats_for_prompt

_FILTER_SYSTEM = (
    "You are an academic document structure filter. "
    "Process a list of extracted section headings from a research paper and return only those "
    "relevant for downstream technical claim extraction.\n"
    "RULES:\n"
    "1. EXCLUDE: Related Work, Literature Review, Limitations, Conclusion, Introduction, "
    "Acknowledgments, References, Appendices, Supplementary Material.\n"
    "2. RETAIN: sections covering methods, algorithms, system design, experiments, results, "
    "theoretical analysis, applications.\n"
    "3. When in doubt, prefer retention.\n"
    "4. Preserve original sequential order.\n"
    "OUTPUT: ONLY a valid JSON array of strings. No markdown, no explanations.\n"
    'Example: ["Methodology", "Experimental Setup", "Results"]'
)

_EXTRACT_SYSTEM = (
    "You are an expert technical reviewer for machine learning research. "
    "Extract verifiable factual claims from a section of a research paper.\n"
    "DEFINITION: A 'verifiable claim' is a specific, concrete statement that can be confirmed or "
    "refuted by inspecting the code repository, configuration files, or execution logs.\n"
    "RULES:\n"
    "- EXTRACT only specific, technical statements about datasets, models, training procedures, "
    "metrics, or infrastructure.\n"
    "- EXCLUDE vague descriptions, motivations, references to prior work, subjective evaluations.\n"
    "GOOD EXAMPLES:\n"
    "- 'ResNet-50 was used as the backbone'\n"
    "- 'The dataset was split 80/10/10 for train/val/test'\n"
    "- 'Adam optimizer with lr=0.001 was used'\n"
    "- 'The model was trained for 50 epochs'\n"
    "BAD EXAMPLES (DO NOT EXTRACT):\n"
    "- 'a deep learning model was used' (vague)\n"
    "- 'we chose this approach because it is efficient' (motivation)\n"
    "OUTPUT SCHEMA (every object must have exactly these fields):\n"
    "- 'claim': string, self-contained sentence\n"
    "- 'original_text': string, verbatim fragment ≤30 words\n"
    "- 'category': one of [dataset, model_architecture, training_procedure, evaluation_metric, "
    "numerical_result, baseline_comparison, data_preprocessing, infrastructure]\n"
    "- 'value': string or null — the specific value if present\n"
    "- 'verifiability': one of [high, medium, low]\n"
    "OUTPUT FORMAT: ONLY a valid JSON array. No markdown, no preamble. Return [] if nothing found."
)

_DEDUP_SYSTEM = (
    "You are a technical claim deduplication engine. Process a list of ML paper claims: "
    "merge duplicates and flag factual contradictions.\n"
    "RULES:\n"
    "1. MERGE DUPLICATES: consolidate into the most specific version.\n"
    "2. FLAG CONTRADICTIONS: if claims disagree on the same fact, keep both and set "
    "'contradiction': true.\n"
    "3. PRESERVE all claims even if they seem incorrect — accuracy is checked later.\n"
    "SCHEMA: every object must have: claim, original_text, category, value, verifiability, "
    "contradiction (bool, default false).\n"
    "OUTPUT: ONLY a valid JSON array. No markdown, no preamble. Return [] if empty."
)

_VERIFY_SYSTEM = (
    "You are a code reviewer checking which technical claims from a research paper are implemented "
    "in the provided repository source code.\n"
    "For each claim determine whether the code contains evidence of its implementation.\n"
    "OUTPUT: a JSON array with one object per claim (same order, 0-based index):\n"
    '[\n  {"index": 0, "implemented": true, "confidence": "high", '
    '"evidence_file": "train.py", "explanation": "Adam optimizer set at line 42"},\n  ...\n]\n'
    "confidence: 'high' = directly visible, 'medium' = inferable, 'low' = uncertain.\n"
    "implemented=false when no evidence found. Return ONLY the JSON array."
)

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
    """Parse raw LLM output as a JSON array, raising JsonParseError on failure."""
    cleaned = JsonProcessor.process_text(raw)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise JsonParseError(f"JSON decode failed: {e}") from e
    if not isinstance(data, list):
        raise JsonParseError(f"Expected JSON array, got {type(data).__name__}")
    return data


def _llm_parse_list(config: VkrConfig, system: str, user: str) -> list:
    """
    Call send_and_parse with _parse_json_list as the parser.
    OSA's send_and_parse handles retries and logging.
    """
    return config.model_handler.send_and_parse(user, _parse_json_list, system)


def _csv_files(flat_paths: list[str], max_files: int = 5) -> list[str]:
    return [p for p in flat_paths if _CSV_PATTERN.search(p)][:max_files]


def collect_csv_stats(
    flat_paths: list[str],
    clone_dir: str,
    on_progress: Progress = None,
    max_files: int = 5,
) -> list[dict]:
    paths = _csv_files(flat_paths, max_files)
    results = []
    for i, path in enumerate(paths):
        if on_progress:
            on_progress(f"Analysing data file {path}...", i / max(len(paths), 1))
        try:
            with open(os.path.join(clone_dir, path), encoding="utf-8", errors="replace") as f:
                content = f.read()
            stats = analyze_csv(content, filename=path)
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


def extract_claims(
    paper_sections: list[dict],
    config: VkrConfig,
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
    retained_names: list[str] = _llm_parse_list(
        config,
        _FILTER_SYSTEM,
        (
            "Below is the list of section headings extracted from the target paper:\n"
            f"{json.dumps(section_names, ensure_ascii=False)}\n"
            "Filter the list and return ONLY a JSON array of the retained section names."
        ),
    )
    _prog(f"Retained {len(retained_names)} sections for claim extraction.", 0.15)

    # Step 2: extract claims per section
    all_raw_claims: list[str] = []
    section_map = {s["name"]: s.get("text", "") for s in paper_sections}

    for i, name in enumerate(retained_names):
        text = section_map.get(name, "")
        if not text.strip():
            continue
        _prog(f"Extracting claims from '{name}'...", 0.15 + 0.50 * (i / max(len(retained_names), 1)))
        claims_list: list = _llm_parse_list(
            config,
            _EXTRACT_SYSTEM,
            (
                f"Analyze the following report section and extract all verifiable factual claims:\n\n"
                f"{text}\n\nReturn ONLY the JSON array."
            ),
        )
        all_raw_claims.append(json.dumps(claims_list, ensure_ascii=False))

    if not all_raw_claims:
        return []

    # Step 3: deduplicate
    _prog("Deduplicating claims...", 0.70)
    final_claims: list = _llm_parse_list(
        config,
        _DEDUP_SYSTEM,
        (
            "Below are claims extracted from all sections. Deduplicate and flag contradictions:\n"
            f"{json.dumps(all_raw_claims, ensure_ascii=False)}\n"
            "Return ONLY the final processed JSON array."
        ),
    )
    _prog(f"Extracted {len(final_claims)} unique claims.", 1.0)
    return final_claims


def verify_claims(
    claims: list[dict],
    flat_paths: list[str],
    config: VkrConfig,
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
            "stats": {"total": 0, "implemented": 0, "implementation_rate": 0.0, "implementation_rate_pct": 0},
        }

    _prog("Identifying candidate source files...", 0.0)
    candidates = _candidate_files(flat_paths)
    code_snippets: list[str] = []
    for path in candidates:
        try:
            with open(os.path.join(config.clone_dir, path), encoding="utf-8", errors="replace") as f:
                content = f.read()
            code_snippets.append(f"### {path}\n{_truncate(content)}")
        except Exception as e:
            code_snippets.append(f"### {path}\n[could not read: {e}]")
        _prog(f"Read {path}", 0.1 + 0.3 * (len(code_snippets) / max(len(candidates), 1)))

    has_dataset_claims = any(c.get("category") in ("dataset", "data_preprocessing") for c in claims)
    csv_section = ""
    csv_stats_list: list[dict] = []
    if has_dataset_claims:
        _prog("Analysing data files (CSV/TSV)...", 0.35)

        def _csv_prog(msg: str, pct: float) -> None:
            _prog(msg, 0.35 + pct * 0.05)

        csv_stats_list = collect_csv_stats(flat_paths, config.clone_dir, on_progress=_csv_prog)
        if csv_stats_list:
            csv_blocks = [format_csv_stats_for_prompt(s) for s in csv_stats_list]
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

    verifications: list = _llm_parse_list(config, _VERIFY_SYSTEM, user_content)
    _prog("Verification complete.", 1.0)

    ver_by_index = {v.get("index", i): v for i, v in enumerate(verifications)}
    annotated: list[dict] = []
    for i, claim in enumerate(claims):
        ver = ver_by_index.get(i, {})
        annotated.append({
            **claim,
            "implementation": {
                "implemented": ver.get("implemented", False),
                "confidence": ver.get("confidence", "low"),
                "evidence_file": ver.get("evidence_file"),
                "explanation": ver.get("explanation", ""),
            },
        })

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
