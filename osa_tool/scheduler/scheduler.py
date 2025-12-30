import os

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.scheduler.response_validation import PromptConfig
from osa_tool.scheduler.workflow_manager import WorkflowManager
from osa_tool.ui.plan_editor import PlanEditor
from osa_tool.ui.web_plan_editor import WebPlanEditor
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder, PromptLoader
from osa_tool.utils.response_cleaner import JsonProcessor
from osa_tool.utils.utils import extract_readme_content, parse_folder_name


class ModeScheduler:
    """
    Task scheduling module that determines which actions should be performed
    based on repository analysis, configuration, and selected execution mode.
    """

    def __init__(
        self,
        config_loader: ConfigLoader,
        sourcerank: SourceRank,
        prompts: PromptLoader,
        args,
        workflow_manager: WorkflowManager,
        metadata: RepositoryMetadata,
    ):
        self.mode = args.mode
        self.args = args
        self.config = config_loader.config
        self.sourcerank = sourcerank
        self.workflow_manager = workflow_manager
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.repo_url = self.config.git.repository
        self.metadata = metadata
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.prompts = prompts
        self.plan = self._select_plan()

    @staticmethod
    def _basic_plan() -> dict:
        """Return default plan for 'basic' mode."""
        plan = {
            "about": True,
            "community_docs": True,
            "organize": True,
            "readme": True,
            "report": True,
        }
        return plan

    def _select_plan(self) -> dict:
        """
        Build a task plan based on the selected mode.

        Returns:
            dict: Prepared plan dictionary.
        """
        plan = dict(vars(self.args))

        if self.mode == "basic":
            logger.info("Basic mode selected for task scheduler.")
            for key, value in self._basic_plan().items():
                plan[key] = value

        elif self.mode == "advanced":
            logger.info("Advanced mode selected for task scheduler.")

        elif self.mode == "auto":
            logger.info("Auto mode selected for task scheduler.")
            auto_plan = self._make_request_for_auto_mode()

            if not self.sourcerank.requirements_presence():
                auto_plan["requirements"] = True

            actual_workflows_plan = self.workflow_manager.build_actual_plan(self.sourcerank)

            for key, value in actual_workflows_plan.items():
                auto_plan[key] = value

            for key, value in auto_plan.items():
                plan[key] = value
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")

        if self.args.web_mode:
            logger.info("Web mode enabled, returning plan for web interface.")
            if self.mode in ["basic", "advanced"]:
                return plan

            web_plan_handler = WebPlanEditor(plan)
            logger.info(f"Plan saved for web at {web_plan_handler.get_plan_path()}")

            updated_plan = web_plan_handler.get_updated_plan()
            return updated_plan
        return PlanEditor(self.workflow_manager.workflow_keys).confirm_action(plan)

    def _make_request_for_auto_mode(self) -> dict:
        """
        Send prompt to model and parse JSON response to build auto mode plan.

        Returns:
            dict: Plan parsed from model response.
        """
        prompt = PromptBuilder.render(
            self.prompts.get("scheduler.main_prompt"),
            license_presence=self.sourcerank.license_presence(),
            about_section=self.metadata.description,
            repository_tree=self.sourcerank.tree,
            readme_content=extract_readme_content(self.base_path),
        )

        data = self.model_handler.send_and_parse(
            prompt=prompt, parser=lambda raw: PromptConfig.safe_validate(JsonProcessor.parse(raw, expected_type=dict))
        )
        return data.model_dump()
