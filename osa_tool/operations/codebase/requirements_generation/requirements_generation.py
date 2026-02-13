import subprocess
from pathlib import Path

from osa_tool.config.settings import ConfigManager
from osa_tool.core.llm.llm import ModelHandlerFactory
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.scheduler.plan import Plan
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.utils import parse_folder_name


class RequirementsGenerator:
    """
    Generates a `requirements.txt` file for a repository using `pipreqs`.

    This class analyzes the source code of the repository to detect imported
    Python packages and produces a dependency list.
    """

    def __init__(self, config_manager: ConfigManager, plan: Plan):
        self.config_manager = config_manager
        self.repo_url = config_manager.get_git_settings().repository
        self.repo_path = Path(parse_folder_name(self.repo_url)).resolve()
        self.events: list[OperationEvent] = []
        self.plan = plan
        self.prompts = self.config_manager.get_prompts()
        self.model_handler = ModelHandlerFactory.build(self.config_manager.config)

    def generate(self) -> dict:
        logger.info(f"Starting the generation of requirements for: {self.repo_url}")
        self.plan.mark_started("requirements")
        if not self._validate_repo_path():
            self.plan.mark_failed("requirements")
            return {
                "result": None,
                "events": self.events,
            }

        req_file_path = self.repo_path / "requirements.txt"
        pyproject_path = self.repo_path / "pyproject.toml"

        old_context = self._get_existing_context(req_file_path, pyproject_path)

        # Scan with notebooks
        try:
            logger.info("Attempting scan with notebooks...")
            self._run_pipreqs(scan_notebooks=True)
            logger.info("Requirements generated successfully with notebook scanning")
            self._add_event(EventKind.GENERATED, mode="scan-notebooks")

        except subprocess.CalledProcessError as e:
            logger.warning("Standard scan failed. Retrying without notebooks...")
            self._add_event(EventKind.FAILED, mode="scan-notebooks", data={"stderr": e.stderr})

            # Scan without notebooks
            logger.info("Retrying requirements generation WITHOUT notebooks...")
            try:
                self._run_pipreqs(scan_notebooks=False)
                logger.info("Requirements generated successfully (excluding notebooks)")
                self._add_event(EventKind.GENERATED, mode="no-notebooks")

            except subprocess.CalledProcessError as e_retry:
                logger.error("Fatal error: Could not generate requirements.")
                self._add_event(EventKind.FAILED, mode="no-notebooks", data={"stderr": e_retry.stderr})
                self.plan.mark_failed("requirements")
                raise

        # LLM Refinement
        if old_context:
            logger.info("Merging requirements versions using LLM...")
            self._refine_with_llm(req_file_path, old_context)

        self.plan.mark_done("requirements")
        return self._result_dict()

    def _refine_with_llm(self, req_file_path: Path, old_context: str) -> None:
        """Reads generated reqs, merges with old context via LLM, and rewrites file."""
        try:
            new_requirements = req_file_path.read_text(encoding="utf-8").strip()
            if not new_requirements:
                return

            prompt_template = self.prompts.get("requirements.merge_requirements")
            prompt = PromptBuilder.render(
                prompt_template,
                old_requirements=old_context,
                new_requirements=new_requirements
            )

            response = self.model_handler.send_request(prompt)
            merged_content = self._clean_llm_response(response)

            if merged_content:
                req_file_path.write_text(merged_content, encoding="utf-8")
                logger.info("Requirements successfully refined with LLM.")
                self._add_event(EventKind.REFINED, mode="llm-merge")
        except Exception as e:
            logger.error(f"Error during LLM refinement: {e}")

    def _clean_llm_response(self, text: str) -> str:
        text = text.strip()
        if "```" in text:
            lines = text.splitlines()
            if lines[0].startswith("```"): lines = lines[1:]
            if lines and lines[-1].startswith("```"): lines = lines[:-1]
            return "\n".join(lines).strip()
        return text

    def _get_existing_context(self, req_path: Path, pyproject_path: Path) -> str:
        """Reads existing dependencies to preserve versions."""
        context = ""
        if req_path.exists():
            try:
                content = req_path.read_text(encoding="utf-8").strip()
                if content:
                    context += f"--- EXISTING REQUIREMENTS.TXT ---\n{content}\n"
            except Exception as e:
                logger.warning(f"Could not read requirements.txt: {e}")

        if pyproject_path.exists():
            try:
                content = pyproject_path.read_text(encoding="utf-8").strip()
                if content:
                    context += f"--- EXISTING PYPROJECT.TOML ---\n{content}\n"
            except Exception as e:
                logger.warning(f"Could not read pyproject.toml: {e}")

        return context.strip()

    def _validate_repo_path(self) -> bool:
        """Check that the repository directory exists."""
        if not self.repo_path.exists():
            logger.error(f"Repo path does not exist: {self.repo_path}")
            self._add_event(
                EventKind.FAILED,
                mode="init",
                data={"error": "repository path does not exist"},
            )
            return False
        return True

    def _run_pipreqs(self, scan_notebooks: bool) -> subprocess.CompletedProcess:
        """Run pipreqs with or without notebook scanning."""
        base_cmd = ["pipreqs", "--force", "--encoding", "utf-8"]
        if scan_notebooks:
            base_cmd.append("--scan-notebooks")

        cmd = base_cmd + [str(self.repo_path)]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        logger.debug(result)
        return result

    def _add_event(self, kind: EventKind, mode: str, data: dict | None = None):
        """Append a structured OperationEvent."""
        payload = {"tool": "pipreqs", "mode": mode}
        if data:
            payload.update(data)

        self.events.append(
            OperationEvent(
                kind=kind,
                target="requirements.txt",
                data=payload,
            )
        )

    def _result_dict(self) -> dict:
        """Return the standard structured result."""
        return {
            "result": {"path": str(self.repo_path / "requirements.txt")},
            "events": self.events,
        }
