import subprocess
from pathlib import Path
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.models.models import ModelHandlerFactory
from osa_tool.config.settings import ConfigManager
from osa_tool.utils.utils import parse_folder_name


class RequirementsGenerator:
    """
    Generates and refines requirements.txt using pipreqs and LLM.
    """

    def __init__(self, config_manager: ConfigManager):
        """
        Initializes the requirements generator.

        Args:
            config_manager (ConfigManager): configuration manager.
        """
        self.config_manager = config_manager
        self.prompts = self.config_manager.get_prompts()
        self.model_handler = ModelHandlerFactory.build(self.config_manager.config)

    def generate(self, repo_url: str) -> None:
        """
        Main method to generate requirements.txt.
        Reads existing requirements.
        Runs pipreqs to get actual dependencies.
        Merges them using LLM to keep versions but remove unused libs.

        Args:
            repo_url (str): URL of the repository.
        """
        logger.info("Starting the generation of requirements")
        repo_path = Path(parse_folder_name(repo_url)).resolve()
        req_file_path = repo_path / "requirements.txt"

        old_requirements = ""
        if req_file_path.exists():
            try:
                old_requirements = req_file_path.read_text(encoding="utf-8").strip()
                if old_requirements:
                    logger.info("Found existing requirements.txt, reading context...")
            except Exception as e:
                logger.warning(f"Could not read existing requirements.txt: {e}")

        if not self._run_pipreqs(repo_path):
            return

        try:
            new_requirements = req_file_path.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.error(f"Failed to read generated requirements.txt: {e}")
            return

        if not old_requirements:
            logger.info("No previous requirements context found. Keeping pipreqs generation.")
            return

        # We have both old and new reqs - merging via LLM.
        logger.info("Merging requirements versions using LLM...")
        merged_content = self._merge_requirements_via_llm(old_requirements, new_requirements)

        if merged_content:
            try:
                req_file_path.write_text(merged_content, encoding="utf-8")
                logger.info(f"Requirements successfully merged and updated at: {req_file_path}")
            except Exception as e:
                logger.error(f"Failed to write merged requirements: {e}")
        else:
            logger.warning("LLM returned empty content, keeping pipreqs version.")

    def _run_pipreqs(self, repo_path: Path) -> bool:
        """
        Runs pipreqs subprocess.

        Args:
            repo_path (Path): Path to the repository.

        Returns:
            bool: True if pipreqs was successfully run.
        """
        try:
            result = subprocess.run(
                ["pipreqs", "--scan-notebooks", "--force", "--encoding", "utf-8", repo_path],
                capture_output=True,
                text=True,
                check=True,
            )
            logger.info(f"Requirements via pipreqs generated successfully at: {repo_path}")
            logger.debug(result)
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Error while generating project's requirements via pipreqs: {e.stderr}")
            return False

    def _merge_requirements_via_llm(self, old_reqs: str, new_reqs: str) -> str:
        """
        Sends request to LLM to merge requirements.

        Args:
            old_reqs (str): Content of the old requirements file.
            new_reqs (str): Content of the new requirements file.

        Returns:
            str: Content of the merged requirements file.
        """
        try:
            # Getting prompt from yaml
            prompt_template = self.prompts.get("requirements.merge_requirements")

            prompt = PromptBuilder.render(prompt_template, old_requirements=old_reqs, new_requirements=new_reqs)

            # sync because it's a single operation
            response = self.model_handler.send_request(prompt)

            return self._clean_llm_response(response)
        except Exception as e:
            logger.error(f"Error during LLM merge request: {e}")
            return ""

    def _clean_llm_response(self, text: str) -> str:
        """
        Removes markdown code blocks from LLM response.

        Args:
            text (str): Content of the response.

        Returns:
            str: Clean content of the response.
        """
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text
