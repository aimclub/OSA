"""VKR repository quality checks — uses OSA's LLM and the already-cloned repo."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Optional

from osa_tool.utils.response_cleaner import JsonParseError, JsonProcessor

_README_RE = re.compile(r"^README(\.\w+)?$", re.IGNORECASE)
_LICENSE_RE = re.compile(r"^(LICENSE|LICENCE|COPYING|NOTICE)(\.\w+)?$", re.IGNORECASE)
_REQUIRE_RE = re.compile(r"^(requirements\.txt|pyproject\.toml)$", re.IGNORECASE)
_TEST_DIR_RE = re.compile(r"^(tests?|__tests__|spec|specs|e2e)$", re.IGNORECASE)

README_MIN_CHARS = 200
APP_TYPES = {"app"}
DATA_TYPES = {"algorithm_experiments", "model_training_experiments"}
EXPERIMENT_TYPES = {"algorithm_experiments", "model_training_experiments"}

_PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")

_SYSTEM_JSON = "You are a code repository analyst. Always respond with valid JSON and nothing else."


@dataclass
class VkrConfig:
    """Thin config object threaded through all VKR check/claim functions."""

    clone_dir: str  # absolute path to the already-cloned repository
    repo_url: str  # original URL — used only in report metadata
    repo: Any  # git.Repo (GitPython) — for commit count
    model_handler: Any  # osa_tool.core.llm.llm.ModelHandler


# ── Helpers ───────────────────────────────────────────────────────────────────


def _load_prompt(name: str) -> str:
    with open(os.path.join(_PROMPTS_DIR, name), encoding="utf-8") as f:
        return f.read()


def _sample_tree(all_paths: list, max_per_dir: int = 5, max_total: int = 500) -> list:
    dir_counts: dict = defaultdict(int)
    sampled = []
    for path in all_paths:
        parts = path.replace("\\", "/").split("/")
        parent = "/".join(parts[:-1]) if len(parts) > 1 else ""
        if dir_counts[parent] < max_per_dir:
            sampled.append(path)
            dir_counts[parent] += 1
        if len(sampled) >= max_total:
            break
    return sampled


def _call_llm(prompt: str, config: VkrConfig, system: str = None) -> dict:
    """Single-turn JSON call via OSA's send_and_parse."""
    try:
        result = config.model_handler.send_and_parse(prompt, JsonProcessor.parse, system or _SYSTEM_JSON)
        return result if isinstance(result, dict) else {"error": "unexpected_type"}
    except (JsonParseError, Exception) as exc:
        return {"error": "llm_parse_failed", "raw": str(exc)[:500]}


def _read_file(clone_dir: str, path: str) -> str:
    with open(os.path.join(clone_dir, path), encoding="utf-8", errors="replace") as f:
        return f.read()


def _commit_count(repo: Any, threshold: int = 5) -> int:
    count = 0
    for _ in repo.iter_commits(max_count=threshold + 1):
        count += 1
    return count


# ── Checks ────────────────────────────────────────────────────────────────────


def check_readme(flat_paths: list, config: VkrConfig) -> dict:
    for path in flat_paths:
        if _README_RE.match(os.path.basename(path)):
            try:
                content = _read_file(config.clone_dir, path)
                char_count = len(content)
                return {
                    "present": True,
                    "meaningful": char_count >= README_MIN_CHARS,
                    "char_count": char_count,
                    "matched_file": path,
                }
            except Exception as e:
                return {"present": True, "meaningful": None, "matched_file": path, "error": str(e)}
    return {"present": False, "meaningful": False, "matched_file": None}


def check_license(flat_paths: list) -> dict:
    for path in flat_paths:
        if _LICENSE_RE.match(os.path.basename(path)):
            return {"present": True, "matched_file": path}
    return {"present": False, "matched_file": None}


def check_requirements(flat_paths: list) -> dict:
    for path in flat_paths:
        if _REQUIRE_RE.match(os.path.basename(path)):
            return {"applicable": True, "present": True, "matched_file": path}
    return {"applicable": True, "present": False, "matched_file": None}


def check_execution_files(flat_paths: list, config: VkrConfig) -> dict:
    prompt = _load_prompt("execution_files.txt").replace("{file_list}", "\n".join(flat_paths))
    result = _call_llm(prompt, config)
    if "error" in result:
        return {"present": False, "error": result["error"], "llm_suggested": [], "verified": []}
    suggested = result.get("entry_points", [])
    verified = [p for p in suggested if p in set(flat_paths)]
    return {"present": bool(verified), "llm_suggested": suggested, "verified": verified}


def check_repo_type(all_paths: list, config: VkrConfig) -> dict:
    prompt = _load_prompt("repo_type.txt").replace("{file_list}", "\n".join(_sample_tree(all_paths)))
    result = _call_llm(prompt, config)
    if "error" in result:
        return {
            "value": "algorithm_experiments",
            "confidence": "low",
            "reasoning": result.get("error", ""),
            "error": result["error"],
        }
    return {
        "value": result.get("repo_type", "algorithm_experiments"),
        "confidence": result.get("confidence", "low"),
        "reasoning": result.get("reasoning", ""),
    }


def check_tests(flat_paths: list, all_paths: list, config: VkrConfig) -> dict:
    for path in all_paths:
        for part in path.replace("\\", "/").split("/")[:-1]:
            if _TEST_DIR_RE.match(part):
                return {"applicable": True, "present": True, "method": "regex", "files": [part + "/"]}
    prompt = _load_prompt("test_files.txt").replace("{file_list}", "\n".join(flat_paths))
    result = _call_llm(prompt, config)
    if "error" in result:
        return {"applicable": True, "present": False, "error": result["error"], "files": []}
    verified = [p for p in result.get("test_files", []) if p in set(flat_paths)]
    return {"applicable": True, "present": bool(verified), "method": "llm", "files": verified}


def check_data_files(flat_paths: list, config: VkrConfig) -> dict:
    prompt = _load_prompt("data_files.txt").replace("{file_list}", "\n".join(flat_paths))
    result = _call_llm(prompt, config)
    if "error" in result:
        return {"applicable": True, "present": False, "error": result["error"], "files": []}
    verified = [p for p in result.get("data_files", []) if p in set(flat_paths)]
    return {"applicable": True, "present": bool(verified), "files": verified}


def check_experiment_scripts(flat_paths: list, config: VkrConfig, readme_content: str = "") -> dict:
    readme_section = f"README content:\n{readme_content[:3000]}" if readme_content else ""
    prompt = (
        _load_prompt("experiment_scripts.txt")
        .replace("{file_list}", "\n".join(flat_paths))
        .replace("{readme_section}", readme_section)
    )
    result = _call_llm(prompt, config)
    if "error" in result:
        return {"applicable": True, "present": False, "error": result["error"], "files": []}
    verified = [p for p in result.get("experiment_files", []) if p in set(flat_paths)]
    return {"applicable": True, "present": bool(verified), "files": verified}


def check_commits(config: VkrConfig) -> dict:
    count = _commit_count(config.repo, threshold=5)
    return {"present": count > 5, "count": count}


def check_syntax(flat_paths: list, clone_dir: str) -> dict:
    py_files = [p for p in flat_paths if p.endswith(".py")]
    if not py_files:
        return {"ok": True, "errors": [], "summary": "no Python files"}
    result = subprocess.run(
        [sys.executable, "-m", "compileall", "-q", "."],
        cwd=clone_dir,
        capture_output=True,
        text=True,
        timeout=60,
    )
    error_lines = [
        line.strip()
        for line in (result.stdout + result.stderr).splitlines()
        if line.strip() and ("SyntaxError" in line or "***" in line or "Error" in line)
    ]
    ok = result.returncode == 0
    summary = f"all {len(py_files)} files ok" if ok else f"{len(error_lines)} error(s) in {len(py_files)} files"
    return {"ok": ok, "errors": error_lines[:10], "summary": summary}


def check_docstrings(flat_paths: list, clone_dir: str) -> dict:
    py_files = [p for p in flat_paths if p.endswith(".py")]
    if not py_files:
        return {"coverage_pct": None, "documented": 0, "total": 0, "summary": "no Python files"}
    total = documented = 0
    for rel_path in py_files:
        try:
            with open(os.path.join(clone_dir, rel_path), encoding="utf-8", errors="replace") as f:
                tree = ast.parse(f.read())
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                total += 1
                if (
                    node.body
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Constant)
                    and isinstance(node.body[0].value.value, str)
                ):
                    documented += 1
    if total == 0:
        return {"coverage_pct": 0, "documented": 0, "total": 0, "summary": "no functions or classes found"}
    pct = round(documented / total * 100)
    return {
        "coverage_pct": pct,
        "documented": documented,
        "total": total,
        "summary": f"{pct}% ({documented}/{total} functions/classes)",
    }


# ── File-tree builder (replaces github_client.get_tree) ───────────────────────


def build_file_tree(clone_dir: str):
    """Walk the local clone and return (flat_paths, all_paths)."""
    flat_paths: list[str] = []
    all_paths: list[str] = []
    for root, dirs, files in os.walk(clone_dir):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d != "__pycache__"]
        for name in files:
            if name.startswith("."):
                continue
            rel = os.path.relpath(os.path.join(root, name), clone_dir).replace(os.sep, "/")
            flat_paths.append(rel)
            all_paths.append(rel)
        for name in dirs:
            rel = os.path.relpath(os.path.join(root, name), clone_dir).replace(os.sep, "/")
            all_paths.append(rel)
    return flat_paths, all_paths


# ── Orchestrator ──────────────────────────────────────────────────────────────

Progress = Optional[Callable[[str, float], None]]


def run_all_checks(
    flat_paths: list,
    all_paths: list,
    config: VkrConfig,
    on_progress: Progress = None,
) -> dict:
    def _progress(msg: str, pct: float) -> None:
        print(msg, file=sys.stderr)
        if on_progress:
            on_progress(msg, pct)

    results: dict = {}

    _progress("Checking README...", 0.10)
    results["readme"] = check_readme(flat_paths, config)

    _progress("Checking license...", 0.15)
    results["license"] = check_license(flat_paths)

    _progress("Checking commits...", 0.20)
    results["commits"] = check_commits(config)

    _progress("Identifying entry-point files...", 0.30)
    results["execution_files"] = check_execution_files(flat_paths, config)

    _progress("Classifying repository type...", 0.40)
    repo_type_result = check_repo_type(all_paths, config)
    results["repo_type"] = repo_type_result
    repo_type = repo_type_result.get("value", "algorithm_experiments")

    if repo_type in APP_TYPES:
        results["requirements"] = {"applicable": False}
        _progress("Checking tests...", 0.50)
        results["tests"] = check_tests(flat_paths, all_paths, config)
    else:
        _progress("Checking requirements file...", 0.50)
        results["requirements"] = check_requirements(flat_paths)
        results["tests"] = {"applicable": False}

    if repo_type in DATA_TYPES:
        _progress("Identifying data files...", 0.60)
        results["data_files"] = check_data_files(flat_paths, config)
    else:
        results["data_files"] = {"applicable": False}

    if repo_type in EXPERIMENT_TYPES:
        _progress("Identifying experiment scripts...", 0.70)
        readme_content = ""
        readme_check = results.get("readme", {})
        if readme_check.get("present") and readme_check.get("matched_file"):
            try:
                readme_content = _read_file(config.clone_dir, readme_check["matched_file"])
            except Exception:
                pass
        results["experiment_scripts"] = check_experiment_scripts(flat_paths, config, readme_content)
    else:
        results["experiment_scripts"] = {"applicable": False}

    _progress("Checking syntax...", 0.85)
    results["syntax"] = check_syntax(flat_paths, config.clone_dir)
    _progress("Measuring docstring coverage...", 0.92)
    results["docstrings"] = check_docstrings(flat_paths, config.clone_dir)

    return results
