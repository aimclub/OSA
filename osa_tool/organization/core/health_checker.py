"""Health checker for validating project build and syntax."""

import os
import re
import json
import sys
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple

from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor, JsonParseError
from osa_tool.core.llm.llm import ModelHandler
from osa_tool.organization.core.utils import atomic_write_file


class HealthChecker:
    """
    Checks project health by running build commands or syntax checks.

    Can attempt LLM‑based fixes for detected errors. Provides comprehensive
    health checking for various project types and can automatically fix
    common issues using AI assistance.
    """

    def __init__(self, base_path: Path, project_type: str, model_handler: ModelHandler, prompts: dict):
        """
        Initialize the health checker.

        Args:
            base_path: Root directory path
            project_type: Type of project (e.g., 'python', 'java')
            model_handler: Handler for LLM interactions
            prompts: Dictionary of prompt templates
        """
        self.base_path = base_path
        self.project_type = project_type
        self.model_handler = model_handler
        self.prompts = prompts

    def _run_command(self, command: List[str], cwd: Optional[Path] = None) -> Tuple[int, str, str]:
        """
        Run a shell command and capture its output.

        Args:
            command: Command and arguments as list
            cwd: Working directory for the command (defaults to base_path)

        Returns:
            Tuple[int, str, str]: Return code, stdout, stderr
        """
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
        except Exception as e:
            logger.warning("Error running command %s: %s", " ".join(command), e)
            return -1, "", str(e)

    def _get_build_command(self) -> Optional[List[str]]:
        """
        Get the appropriate build command for the project type.

        Returns:
            Optional[List[str]]: Build command as list, or None if not applicable
        """
        if self.project_type == "python":
            return [sys.executable, "-m", "compileall", "-q", "."]
        elif self.project_type == "javascript":
            pkg_path = self.base_path / "package.json"
            if pkg_path.exists():
                try:
                    with open(pkg_path, "r", encoding="utf-8") as f:
                        pkg = json.load(f)
                    if "build" in pkg.get("scripts", {}):
                        return ["npm", "run", "build"]
                except:
                    pass
            if any(self.base_path.glob("**/*.ts")):
                return ["npx", "tsc", "--noEmit"]
            return None
        elif self.project_type == "go":
            return ["go", "build", "./..."]
        elif self.project_type == "java":
            if (self.base_path / "pom.xml").exists():
                return ["mvn", "compile", "-DskipTests"]
            if (self.base_path / "build.gradle").exists() or (self.base_path / "build.gradle.kts").exists():
                gradlew = self.base_path / "gradlew"
                if gradlew.exists():
                    return [str(gradlew), "compileJava"]
                return ["gradle", "compileJava"]
        elif self.project_type == "rust":
            return ["cargo", "check"]
        elif self.project_type == "cpp":
            if (self.base_path / "Makefile").exists():
                return ["make", "-n"]
        elif self.project_type == "csharp":
            if list(self.base_path.glob("*.sln")):
                return ["dotnet", "build", "--no-restore"]
        elif self.project_type == "swift":
            if (self.base_path / "Package.swift").exists():
                return ["swift", "build"]
        return None

    def _get_compiler_hint(self) -> Optional[str]:
        """
        Get compiler hint for error parsing.

        Returns:
            Optional[str]: Compiler hint string or None
        """
        if self.project_type == "cpp":
            return "gcc"
        elif self.project_type == "rust":
            return "rust"
        return None

    def _format_errors(self, stdout: str, stderr: str) -> str:
        """
        Format build errors into a readable string.

        Args:
            stdout: Standard output from command
            stderr: Standard error from command

        Returns:
            str: Formatted error message
        """
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
            if any(skip in line.lower() for skip in ["warning:", "note:", "info:"]):
                if "error:" not in line.lower():
                    formatted.append(f"[WARNING] {line}")
                else:
                    formatted.append(f"[ERROR] {line}")
            elif "error:" in line.lower():
                formatted.append(f"[ERROR] {line}")
            elif "failed" in line.lower():
                formatted.append(f"[FAILED] {line}")
            else:
                formatted.append(f"  {line}")
        return "\n".join(formatted)

    def check_health(self) -> Tuple[bool, str]:
        """
        Check project health by running build/syntax checks.

        Returns:
            Tuple[bool, str]: (is_healthy, error_message)
        """
        logger.info("Checking project health for type: %s", self.project_type)
        build_cmd = self._get_build_command()
        if build_cmd:
            logger.debug("Running build command: %s", " ".join(build_cmd))
            ret, stdout, stderr = self._run_command(build_cmd)
            if ret == 0:
                logger.info("Health check passed – no errors found")
                return True, ""
            else:
                error_message = self._format_errors(stdout, stderr)
                logger.warning("Health check failed – build errors detected")
                logger.debug(error_message)
                return False, error_message
        else:
            logger.warning("No build command available for %s, using syntax check fallback", self.project_type)
            return self._syntax_check_fallback()

    def _syntax_check_fallback(self) -> Tuple[bool, str]:
        """
        Fallback syntax check for projects without build commands.

        Returns:
            Tuple[bool, str]: (is_healthy, error_message)
        """
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
                logger.debug(f"  {error}")
            if len(errors) > 10:
                logger.debug("  ... and %d more errors", len(errors) - 10)
            return False, "\n".join(errors)
        logger.info("Syntax check passed – no errors found")
        return True, ""

    def _extract_error_lines(self, file_path: str, error_output: str) -> List[int]:
        """
        Extract line numbers from error output for a specific file.

        Args:
            file_path: Path to the file
            error_output: Error output to parse

        Returns:
            List[int]: List of line numbers with errors
        """
        lines = []
        patterns = [
            rf"{re.escape(file_path)}:(\d+)",
            rf'File "{re.escape(file_path)}", line (\d+)',
            rf"{re.escape(os.path.basename(file_path))}:(\d+)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, error_output):
                try:
                    line_num = int(match.group(1))
                    lines.append(line_num)
                except (ValueError, IndexError):
                    continue
        return lines

    def fix_errors_with_llm(self, error_output: str, context_files: List[str]) -> bool:
        """
        Attempt to fix errors using LLM-based code generation.

        Args:
            error_output: Error output from build/syntax check
            context_files: List of files to consider for fixes

        Returns:
            bool: True if fixes were applied successfully
        """
        if not context_files:
            logger.warning("No files to fix.")
            return False
        file_contents = {}
        for file_path in context_files:
            full = self.base_path / file_path
            if full.is_file():
                try:
                    content = full.read_text(encoding="utf-8")
                    file_contents[file_path] = content
                except Exception as e:
                    logger.warning("Could not read %s: %s", file_path, e)
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
                    full = self.base_path / fpath
                    if atomic_write_file(full, new_content):
                        applied += 1
                        logger.info("Applied fix to %s", fpath)
                    else:
                        logger.error("Failed to write fix to %s", fpath)
            if applied > 0:
                healthy, _ = self.check_health()
                return healthy
            else:
                return False
        except (JsonParseError, Exception) as e:
            logger.error("LLM fixing failed: %s", e)
            return False
