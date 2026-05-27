"""Health checker for validating project build and syntax."""

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from osa_tool.core.llm.llm import ModelHandler
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonParseError, JsonProcessor

from .utils import atomic_write_file


class HealthChecker:
    """
    Checks project health by running build commands or syntax checks.

    Can attempt LLM-based fixes for detected errors. When the required
    local toolchain is missing, the check is skipped instead of blocking
    the whole reorganization flow.
    """

    def __init__(self, base_path: Path, project_type: str, model_handler: ModelHandler, prompts: dict):
        self.base_path = base_path
        self.project_type = project_type
        self.model_handler = model_handler
        self.prompts = prompts

    def _run_command(self, command: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        if cwd is None:
            cwd = self.base_path
        try:
            proc = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=120)
            return proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired:
            logger.warning("Command timed out: %s", " ".join(command))
            return -1, "", "Timeout"
        except FileNotFoundError:
            logger.warning("Command not found: %s", command[0])
            return -1, "", "Command not found"
        except Exception as exc:
            logger.warning("Error running command %s: %s", " ".join(command), exc)
            return -1, "", str(exc)

    @staticmethod
    def _command_is_available(command: List[str]) -> bool:
        executable = command[0]
        if os.path.isabs(executable) or executable.startswith("."):
            return Path(executable).exists()
        return shutil.which(executable) is not None

    def _get_build_command(self) -> Optional[List[str]]:
        if self.project_type == "python":
            return [sys.executable, "-m", "compileall", "-q", "."]
        if self.project_type == "javascript":
            pkg_path = self.base_path / "package.json"
            if pkg_path.exists():
                try:
                    with open(pkg_path, "r", encoding="utf-8") as file_obj:
                        pkg = json.load(file_obj)
                    if "build" in pkg.get("scripts", {}):
                        return ["npm", "run", "build"]
                except Exception:
                    pass
            if any(self.base_path.glob("**/*.ts")):
                return ["npx", "tsc", "--noEmit"]
            return None
        if self.project_type == "go":
            return ["go", "build", "./..."]
        if self.project_type == "java":
            if (self.base_path / "pom.xml").exists():
                return ["mvn", "compile", "-DskipTests"]
            if (self.base_path / "build.gradle").exists() or (self.base_path / "build.gradle.kts").exists():
                gradlew = self.base_path / "gradlew"
                if gradlew.exists():
                    return [str(gradlew), "compileJava"]
                return ["gradle", "compileJava"]
        if self.project_type == "rust":
            return ["cargo", "check"]
        if self.project_type == "cpp" and (self.base_path / "Makefile").exists():
            return ["make", "-n"]
        if self.project_type == "csharp" and list(self.base_path.glob("*.sln")):
            return ["dotnet", "build", "--no-restore"]
        if self.project_type == "swift" and (self.base_path / "Package.swift").exists():
            return ["swift", "build"]
        return None

    def _get_compiler_hint(self) -> Optional[str]:
        if self.project_type == "cpp":
            return "gcc"
        if self.project_type == "rust":
            return "rust"
        return None

    def _format_errors(self, stdout: str, stderr: str) -> str:
        formatted = []
        all_errors = []
        if stderr.strip():
            all_errors.extend(stderr.split("\n"))
        if stdout.strip():
            all_errors.extend(stdout.split("\n"))

        for line in all_errors:
            line = line.strip()
            if not line:
                continue
            lower_line = line.lower()
            if any(skip in lower_line for skip in ["warning:", "note:", "info:"]):
                formatted.append(f"[ERROR] {line}" if "error:" in lower_line else f"[WARNING] {line}")
            elif "error:" in lower_line:
                formatted.append(f"[ERROR] {line}")
            elif "failed" in lower_line:
                formatted.append(f"[FAILED] {line}")
            else:
                formatted.append(f"  {line}")
        return "\n".join(formatted)

    def check_health(self) -> Tuple[bool, str]:
        logger.info("Checking project health for type: %s", self.project_type)
        build_cmd = self._get_build_command()
        if build_cmd:
            if not self._command_is_available(build_cmd):
                logger.warning(
                    "Skipping health check for %s because required tool is unavailable: %s",
                    self.project_type,
                    build_cmd[0],
                )
                return True, ""

            logger.debug("Running build command: %s", " ".join(build_cmd))
            ret, stdout, stderr = self._run_command(build_cmd)
            if ret == 0:
                logger.info("Health check passed - no errors found")
                return True, ""
            if ret == -1 and stderr == "Command not found":
                logger.warning(
                    "Skipping health check for %s because required tool is unavailable: %s",
                    self.project_type,
                    build_cmd[0],
                )
                return True, ""

            error_message = self._format_errors(stdout, stderr)
            logger.warning("Health check failed - build errors detected")
            logger.debug(error_message)
            return False, error_message

        logger.warning("No build command available for %s, using syntax check fallback", self.project_type)
        return self._syntax_check_fallback()

    def _syntax_check_fallback(self) -> Tuple[bool, str]:
        errors = []
        error_count = 0
        logger.debug("Running syntax check fallback for %s", self.project_type)

        if self.project_type == "python":
            python_files = list(self.base_path.rglob("*.py"))
            logger.debug("Checking %d Python files...", len(python_files))
            for py_file in python_files:
                rel_path = py_file.relative_to(self.base_path)
                ret, _, stderr = self._run_command([sys.executable, "-m", "py_compile", str(rel_path)])
                if ret != 0:
                    error_count += 1
                    error_msg = f"Syntax error in {rel_path}: {stderr.strip()}"
                    errors.append(error_msg)
                    logger.debug(error_msg)
        elif self.project_type == "javascript":
            js_files = list(self.base_path.rglob("*.js"))
            logger.debug("Checking %d JavaScript files...", len(js_files))
            for js_file in js_files:
                rel_path = js_file.relative_to(self.base_path)
                ret, _, stderr = self._run_command(["node", "--check", str(rel_path)])
                if ret != 0:
                    error_count += 1
                    error_msg = f"Syntax error in {rel_path}: {stderr.strip()}"
                    errors.append(error_msg)
                    logger.debug(error_msg)

        if errors:
            logger.warning("Syntax check failed! Found %d errors", error_count)
            for error in errors[:10]:
                logger.debug("  %s", error)
            if len(errors) > 10:
                logger.debug("  ... and %d more errors", len(errors) - 10)
            return False, "\n".join(errors)

        logger.info("Syntax check passed - no errors found")
        return True, ""

    def _extract_error_lines(self, file_path: str, error_output: str) -> List[int]:
        lines = []
        patterns = [
            rf"{re.escape(file_path)}:(\d+)",
            rf'File "{re.escape(file_path)}", line (\d+)',
            rf"{re.escape(os.path.basename(file_path))}:(\d+)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, error_output):
                try:
                    lines.append(int(match.group(1)))
                except (ValueError, IndexError):
                    continue
        return lines

    def fix_errors_with_llm(self, error_output: str, context_files: List[str]) -> bool:
        if not context_files:
            logger.warning("No files to fix.")
            return False

        file_contents = {}
        for file_path in context_files:
            full_path = self.base_path / file_path
            if full_path.is_file():
                try:
                    file_contents[file_path] = full_path.read_text(encoding="utf-8")
                except Exception as exc:
                    logger.warning("Could not read %s: %s", file_path, exc)

        if not file_contents:
            return False

        files_context = "\n".join(f"--- {path} ---\n{content}" for path, content in file_contents.items())
        prompt_template = self.prompts.get("repo_organization.fix_prompt")
        if not prompt_template:
            logger.error("fix_prompt not found in configuration")
            return False

        prompt = PromptBuilder.render(
            prompt_template,
            project_type=self.project_type,
            error_output=error_output[:2000],
            files_context=files_context,
        )
        try:
            response = self.model_handler.send_request(prompt)
            logger.debug("LLM fix response: %s", response)
            fixes_data = JsonProcessor.parse(response, expected_type=dict)
            fixes = fixes_data.get("fixes", [])
            applied = 0
            for fix in fixes:
                fpath = fix.get("file")
                new_content = fix.get("new_content")
                if fpath and new_content and fpath in file_contents:
                    full_path = self.base_path / fpath
                    if atomic_write_file(full_path, new_content):
                        applied += 1
                        logger.info("Applied fix to %s", fpath)
                    else:
                        logger.error("Failed to write fix to %s", fpath)
            if applied > 0:
                healthy, _ = self.check_health()
                return healthy
            return False
        except (JsonParseError, Exception) as exc:
            logger.error("LLM fixing failed: %s", exc)
            return False
