"""VKR repository quality checks — uses OSA's LLM and the already-cloned repo."""

from __future__ import annotations

import ast
import json
import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Callable, Optional

from osa_tool.utils.prompts_builder import PromptBuilder, PromptLoader
from osa_tool.utils.response_cleaner import JsonProcessor
from osa_tool.utils.utils import read_file

_README_RE = re.compile(r"^README(\.\w+)?$", re.IGNORECASE)
_LICENSE_RE = re.compile(r"^(LICENSE|LICENCE|COPYING|NOTICE)(\.\w+)?$", re.IGNORECASE)
_REQUIRE_RE = re.compile(r"^(requirements\.txt|pyproject\.toml)$", re.IGNORECASE)
_TEST_DIR_RE = re.compile(r"^(tests?|__tests__|spec|specs|e2e)$", re.IGNORECASE)

README_MIN_CHARS = 200
APP_TYPES = {"app"}
DATA_TYPES = {"algorithm_experiments", "model_training_experiments"}
EXPERIMENT_TYPES = {"algorithm_experiments", "model_training_experiments"}
_VALID_REPO_TYPES = APP_TYPES | EXPERIMENT_TYPES

_PROMPTS = PromptLoader()


@dataclass
class VkrConfig:
    """Thin config object threaded through all VKR check/claim functions."""

    clone_dir: str  # absolute path to the already-cloned repository
    repo_url: str  # original URL — used only in report metadata
    repo: Any  # git.Repo (GitPython) — for commit count
    model_handler: Any  # osa_tool.core.llm.llm.ModelHandler


# ── Helpers ───────────────────────────────────────────────────────────────────


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


def build_file_tree(clone_dir: str):
    """Walk the local clone and return *(flat_paths, all_paths)* lists.

    *flat_paths* contains only files; *all_paths* contains both files and
    directories.  Hidden entries and ``__pycache__`` are skipped.
    """
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


class VkrChecker:
    """Runs all VKR quality checks against a cloned repository."""

    def __init__(self, config: VkrConfig) -> None:
        self._config = config

    # ── Private helpers ───────────────────────────────────────────────────────

    def _commit_count(self, threshold: int = 5) -> int:
        count = 0
        for _ in self._config.repo.iter_commits(max_count=threshold + 1):
            count += 1
        return count

    # ── Checks ────────────────────────────────────────────────────────────────

    def check_readme(self, flat_paths: list) -> dict:
        for path in flat_paths:
            if "/" not in path and _README_RE.match(path):
                try:
                    content = read_file(os.path.join(self._config.clone_dir, path))
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

    def check_license(self, flat_paths: list) -> dict:
        for path in flat_paths:
            if "/" not in path and _LICENSE_RE.match(path):
                return {"present": True, "matched_file": path}
        return {"present": False, "matched_file": None}

    def check_requirements(self, flat_paths: list) -> dict:
        for path in flat_paths:
            if "/" not in path and _REQUIRE_RE.match(path):
                return {"applicable": True, "present": True, "matched_file": path}
        return {"applicable": True, "present": False, "matched_file": None}

    def check_execution_files(self, flat_paths: list) -> dict:
        try:
            result = self._config.model_handler.send_and_parse(
                PromptBuilder.render(
                    _PROMPTS.get("vkr_scoring.execution_files"),
                    file_list="\n".join(flat_paths),
                ),
                JsonProcessor.parse,
                _PROMPTS.get("vkr_scoring.system_json"),
            )
        except Exception:
            return {"present": False, "error": "llm_failed", "llm_suggested": [], "verified": []}
        if not isinstance(result, dict):
            return {"present": False, "error": "unexpected_type", "llm_suggested": [], "verified": []}
        suggested = result.get("entry_points", [])
        verified = [p for p in suggested if p in set(flat_paths)]
        return {"present": bool(verified), "llm_suggested": suggested, "verified": verified}

    def check_repo_type(self, all_paths: list) -> dict:
        try:
            result = self._config.model_handler.send_and_parse(
                PromptBuilder.render(
                    _PROMPTS.get("vkr_scoring.repo_type"),
                    file_list="\n".join(_sample_tree(all_paths)),
                ),
                JsonProcessor.parse,
                _PROMPTS.get("vkr_scoring.system_json"),
            )
        except Exception:
            return {"value": "algorithm_experiments", "confidence": "low", "reasoning": "", "error": "llm_failed"}
        if not isinstance(result, dict):
            return {"value": "algorithm_experiments", "confidence": "low", "reasoning": "", "error": "unexpected_type"}
        raw_type = result.get("repo_type", "algorithm_experiments")
        value = raw_type if raw_type in _VALID_REPO_TYPES else "algorithm_experiments"
        return {
            "value": value,
            "confidence": result.get("confidence", "low"),
            "reasoning": result.get("reasoning", ""),
        }

    def check_tests(self, flat_paths: list, all_paths: list) -> dict:
        for path in all_paths:
            for part in path.replace("\\", "/").split("/")[:-1]:
                if _TEST_DIR_RE.match(part):
                    return {"applicable": True, "present": True, "method": "regex", "files": [part + "/"]}
        try:
            result = self._config.model_handler.send_and_parse(
                PromptBuilder.render(
                    _PROMPTS.get("vkr_scoring.test_files"),
                    file_list="\n".join(flat_paths),
                ),
                JsonProcessor.parse,
                _PROMPTS.get("vkr_scoring.system_json"),
            )
        except Exception:
            return {"applicable": True, "present": False, "error": "llm_failed", "files": []}
        if not isinstance(result, dict):
            return {"applicable": True, "present": False, "error": "unexpected_type", "files": []}
        verified = [p for p in result.get("test_files", []) if p in set(flat_paths)]
        return {"applicable": True, "present": bool(verified), "method": "llm", "files": verified}

    def check_data_files(self, flat_paths: list) -> dict:
        try:
            result = self._config.model_handler.send_and_parse(
                PromptBuilder.render(
                    _PROMPTS.get("vkr_scoring.data_files"),
                    file_list="\n".join(flat_paths),
                ),
                JsonProcessor.parse,
                _PROMPTS.get("vkr_scoring.system_json"),
            )
        except Exception:
            return {"applicable": True, "present": False, "error": "llm_failed", "files": []}
        if not isinstance(result, dict):
            return {"applicable": True, "present": False, "error": "unexpected_type", "files": []}
        verified = [p for p in result.get("data_files", []) if p in set(flat_paths)]
        return {"applicable": True, "present": bool(verified), "files": verified}

    def check_experiment_scripts(self, flat_paths: list, readme_content: str = "") -> dict:
        readme_section = f"README content:\n{readme_content[:3000]}" if readme_content else ""
        try:
            result = self._config.model_handler.send_and_parse(
                PromptBuilder.render(
                    _PROMPTS.get("vkr_scoring.experiment_scripts"),
                    file_list="\n".join(flat_paths),
                    readme_section=readme_section,
                ),
                JsonProcessor.parse,
                _PROMPTS.get("vkr_scoring.system_json"),
            )
        except Exception:
            return {"applicable": True, "present": False, "error": "llm_failed", "files": []}
        if not isinstance(result, dict):
            return {"applicable": True, "present": False, "error": "unexpected_type", "files": []}
        verified = [p for p in result.get("experiment_files", []) if p in set(flat_paths)]
        return {"applicable": True, "present": bool(verified), "files": verified}

    def check_commits(self) -> dict:
        count = self._commit_count(threshold=5)
        return {"present": count >= 5, "count": count}

    def check_syntax(self, flat_paths: list) -> dict:
        py_files = [p for p in flat_paths if p.endswith(".py")]
        if not py_files:
            return {"ok": True, "errors": [], "summary": "no Python files"}
        error_lines = []
        for rel_path in py_files:
            try:
                with open(os.path.join(self._config.clone_dir, rel_path), encoding="utf-8", errors="replace") as f:
                    source = f.read()
                compile(source, rel_path, "exec")
            except SyntaxError as e:
                error_lines.append(f"{rel_path}:{e.lineno}: {e.msg}")
            except Exception as e:
                error_lines.append(f"{rel_path}: {e}")
        ok = len(error_lines) == 0
        summary = f"all {len(py_files)} files ok" if ok else f"{len(error_lines)} error(s) in {len(py_files)} files"
        return {"ok": ok, "errors": error_lines[:10], "summary": summary}

    def check_docstrings(self, flat_paths: list) -> dict:
        py_files = [p for p in flat_paths if p.endswith(".py")]
        if not py_files:
            return {"coverage_pct": None, "documented": 0, "total": 0, "summary": "no Python files"}
        total = documented = 0
        for rel_path in py_files:
            try:
                with open(os.path.join(self._config.clone_dir, rel_path), encoding="utf-8", errors="replace") as f:
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

    def run_all(
        self,
        flat_paths: list,
        all_paths: list,
        on_progress: Progress = None,
    ) -> dict:
        def _progress(msg: str, pct: float) -> None:
            print(msg, file=sys.stderr)
            if on_progress:
                on_progress(msg, pct)

        results: dict = {}

        _progress("Checking README...", 0.10)
        results["readme"] = self.check_readme(flat_paths)

        _progress("Checking license...", 0.15)
        results["license"] = self.check_license(flat_paths)

        _progress("Checking commits...", 0.20)
        results["commits"] = self.check_commits()

        _progress("Identifying entry-point files...", 0.30)
        results["execution_files"] = self.check_execution_files(flat_paths)

        _progress("Classifying repository type...", 0.40)
        repo_type_result = self.check_repo_type(all_paths)
        results["repo_type"] = repo_type_result
        repo_type = repo_type_result.get("value", "algorithm_experiments")

        if repo_type in APP_TYPES:
            results["requirements"] = {"applicable": False}
            _progress("Checking tests...", 0.50)
            results["tests"] = self.check_tests(flat_paths, all_paths)
        else:
            _progress("Checking requirements file...", 0.50)
            results["requirements"] = self.check_requirements(flat_paths)
            results["tests"] = {"applicable": False}

        if repo_type in DATA_TYPES:
            _progress("Identifying data files...", 0.60)
            results["data_files"] = self.check_data_files(flat_paths)
        else:
            results["data_files"] = {"applicable": False}

        if repo_type in EXPERIMENT_TYPES:
            _progress("Identifying experiment scripts...", 0.70)
            readme_content = ""
            readme_check = results.get("readme", {})
            if readme_check.get("present") and readme_check.get("matched_file"):
                try:
                    readme_content = read_file(os.path.join(self._config.clone_dir, readme_check["matched_file"]))
                except Exception:
                    pass
            results["experiment_scripts"] = self.check_experiment_scripts(flat_paths, readme_content)
        else:
            results["experiment_scripts"] = {"applicable": False}

        _progress("Checking syntax...", 0.85)
        results["syntax"] = self.check_syntax(flat_paths)
        _progress("Measuring docstring coverage...", 0.92)
        results["docstrings"] = self.check_docstrings(flat_paths)

        return results
