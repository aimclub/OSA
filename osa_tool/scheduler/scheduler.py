import json
import os

from pydantic import ValidationError

from osa_tool.analytics.metadata import load_data_metadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandler, ModelHandlerFactory
from osa_tool.readmegen.postprocessor.response_cleaner import process_text
from osa_tool.scheduler.prompts import PromptConfig, PromptLoader
from osa_tool.scheduler.workflow_manager import WorkflowManager
from osa_tool.ui.plan_editor import PlanEditor
from osa_tool.ui.web_plan_editor import WebPlanEditor
from osa_tool.utils import extract_readme_content, logger, parse_folder_name


class ModeScheduler:
    """
    Task scheduling module that determines which actions should be performed
    based on repository analysis, configuration, and selected execution mode.
    """

    def __init__(self, config: ConfigLoader, sourcerank: SourceRank, args, workflow_keys: list):
        self.mode = args.mode
        self.args = args
        self.workflow_keys = workflow_keys
        self.config = config.config
        self.sourcerank = sourcerank
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.repo_url = self.config.git.repository
        self.metadata = load_data_metadata(self.repo_url)
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.prompts = PromptLoader().prompts
        self.workflows_plan = {key: value for key, value in vars(self.args).items() if key in self.workflow_keys}
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

            workflow_manager = WorkflowManager(
                base_path=self.base_path,
                sourcerank=self.sourcerank,
                metadata=self.metadata,
                workflows_plan=self.workflows_plan,
            )

            actual_workflows_plan = workflow_manager.build_actual_plan()

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

        return PlanEditor(self.workflow_keys).confirm_action(plan)

    def _make_request_for_auto_mode(self) -> dict:
        """
        Send prompt to model and parse JSON response to build auto mode plan.

        Returns:
            dict: Plan parsed from model response.
        """
        main_prompt = self.prompts.get("main_prompt")
        formatted_prompt = main_prompt.format(
            license_presence=self.sourcerank.license_presence(),
            about_section=self.metadata.description,
            repository_tree=self.sourcerank.tree,
            readme_content=extract_readme_content(self.base_path),
        )

        response = self.model_handler.send_request(formatted_prompt)
        cleaned_response = process_text(response)

        try:
            parsed_json = json.loads(cleaned_response)
            validated_data = PromptConfig.safe_validate(parsed_json)
            return validated_data.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            raise ValueError(f"JSON parsing error: {e}")
