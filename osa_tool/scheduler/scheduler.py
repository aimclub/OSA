import json
import os
import sys

from pydantic import ValidationError

from osa_tool.analytics.metadata import load_data_metadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandlerFactory, ModelHandler
from osa_tool.readmegen.postprocessor.response_cleaner import process_text
from osa_tool.scheduler.prompts import PromptLoader, PromptConfig
from osa_tool.utils import logger, parse_folder_name, extract_readme_content


class ModeScheduler:
    def __init__(self,
                 config: ConfigLoader,
                 sourcerank: SourceRank,
                 args):
        self.mode = args.mode
        self.args = args
        self.config = config.config
        self.sourcerank = sourcerank
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.repo_url = self.config.git.repository
        self.metadata = load_data_metadata(self.repo_url)
        self.base_path = os.path.join(
            os.getcwd(),
            parse_folder_name(self.repo_url)
        )
        self.prompts = PromptLoader().prompts
        self.plan = self._select_plan()


    def _collect_active_args(self) -> dict:
        return {key: value for key, value in vars(self.args).items() if value not in [None, False]}

    @staticmethod
    def _basic_plan() -> dict:
        plan = {
            "generate_report": True,
            "community_docs": True,
            "generate_readme": True,
            "organize": True
        }
        return plan

    def _select_plan(self) -> dict:
        active_args = self._collect_active_args()
        if self.mode == "basic":
            logger.info("Basic mode selected for task scheduler.")
            plan = self._basic_plan()

            for key, value in active_args.items():
                if key not in plan:
                    plan[key] = value
            return plan

        elif self.mode == "advanced":
            logger.info("Advanced mode selected for task scheduler.")
            return active_args

        elif self.mode == "auto":
            logger.info("Auto mode selected for task scheduler.")
            plan = self._make_request_for_auto_mode()

            for key, value in active_args.items():
                plan[key] = value

            self._confirm_action(plan)
            return plan

        raise ValueError(f"Unsupported mode: {self.mode}")

    def _make_request_for_auto_mode(self) -> dict:
        main_prompt = self.prompts.get("main_prompt")
        formatted_prompt = main_prompt.format(
            license_presence=self.sourcerank.license_presence(),
            repository_tree=self.sourcerank.tree,
            readme_content=extract_readme_content(self.base_path),
        )

        response = self.model_handler.send_request(formatted_prompt)
        cleaned_response = process_text(response)

        try:
            parsed_json = json.loads(cleaned_response)
            validated_data = PromptConfig.model_validate(parsed_json)
            return validated_data.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            raise ValueError(f"JSON parsing error: {e}")

    @staticmethod
    def _confirm_action(plan) -> bool:
        print("\nThe following actions are planned based on repository analysis:")
        for key, value in plan.items():
            print(f" - {key}: {value}")

        while True:
            confirm = input("\nDo you want to proceed with these actions? (y/n): ").strip().lower()
            if confirm in ["y", "yes"]:
                return True
            elif confirm in ["n", "no"]:
                logger.info("Operation canceled by user.")
                sys.exit(0)
            else:
                print("Please enter 'y' or 'n'.")
