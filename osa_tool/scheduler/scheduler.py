import os

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory
from osa_tool.scheduler.response_validation import PromptConfig
from osa_tool.scheduler.plan import Plan
from osa_tool.scheduler.workflow_manager import WorkflowManager
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.ui.plan_editor import PlanEditor
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.response_cleaner import JsonProcessor
from osa_tool.utils.utils import extract_readme_content, parse_folder_name


class ModeScheduler:
    """
    Task scheduling module that determines which actions should be performed
        based on repository analysis, configuration, and selected execution mode.
    """


    def __init__(
        self,
        config_manager: ConfigManager,
        sourcerank: SourceRank,
        args,
        workflow_manager: WorkflowManager,
        metadata: RepositoryMetadata,
    ):
        """
        Initializes the ModeScheduler instance with configuration, dependencies, and runtime state.
        
        This constructor sets up the scheduler by processing configuration settings,
        initializing core components, and preparing the execution environment based on
        the selected operating mode.
        
        Args:
            config_manager: Manages configuration settings for the system.
            sourcerank: Provides source code ranking and analysis capabilities.
            args: Command-line arguments containing runtime options.
            workflow_manager: Coordinates workflow execution and task management.
            metadata: Repository metadata including project information.
        
        Initializes the following instance attributes:
            mode (str): Operating mode selected from command-line arguments.
            args (Namespace): Command-line arguments object for runtime configuration.
            config_manager (ConfigManager): Configuration manager instance.
            model_settings (ModelSettings): General model configuration settings.
            sourcerank (SourceRank): Source ranking and analysis component.
            workflow_manager (WorkflowManager): Workflow coordination component.
            model_handler (ModelHandler): Model handler built from factory based on settings.
            repo_url (str): Git repository URL from configuration.
            metadata (RepositoryMetadata): Repository metadata object.
            base_path (str): Base directory path for repository operations.
            prompts (PromptLoader): Loader for prompt templates.
            plan (Plan): Task execution plan based on selected mode.
        
        Why:
        - The constructor centralizes the initialization of all components required for the scheduler's operation.
        - It derives key settings (like model configuration, repository URL, and base path) from the provided configuration manager and arguments, ensuring a consistent runtime environment.
        - The plan is built by calling `_select_plan()` to determine the specific tasks to execute based on the selected mode, enabling flexible, mode-driven behavior.
        """
        self.mode = args.mode
        self.args = args
        self.config_manager = config_manager
        self.model_settings = self.config_manager.get_model_settings("general")
        self.sourcerank = sourcerank
        self.workflow_manager = workflow_manager
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.model_settings)
        self.repo_url = self.config_manager.get_git_settings().repository
        self.metadata = metadata
        self.base_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.prompts = self.config_manager.get_prompts()
        self.plan = Plan(self._select_plan())

    @staticmethod
    def _basic_plan() -> dict:
        """
        Return the default execution plan for the 'basic' operational mode.
        
        This static method defines the minimal set of operations enabled by default when the tool runs in 'basic' mode. The plan is a dictionary where each key represents a specific documentation or enhancement operation, and its boolean value indicates whether that operation is active.
        
        Args:
            None.
        
        Returns:
            A dictionary representing the default plan. The keys and their purposes are:
                - "about": Controls generation of the project's 'about' documentation.
                - "community_docs": Controls generation of community-focused documentation.
                - "organize": Controls repository structure organization operations.
                - "readme": Controls README file generation and enhancement.
                - "report": Controls generation of the technical analysis report.
        
        Why:
            The 'basic' mode provides a standard, lightweight workflow for common repository enhancements. This default plan ensures a consistent starting point without requiring user configuration for these core features.
        """
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
        Build a task plan based on the selected operational mode.
        
        This method constructs the final execution plan by merging the base configuration from command-line arguments with mode-specific enhancements. The plan determines which documentation and repository enhancement operations will be performed.
        
        Args:
            None.
        
        Returns:
            dict: The prepared plan dictionary. In 'basic' and 'advanced' modes, the plan is returned directly. In 'auto' mode, the plan is first processed by the PlanEditor to allow user confirmation or modification before being returned. If 'web_mode' is enabled for 'basic' or 'advanced' modes, the plan is returned without confirmation.
        
        Why:
        - The method centralizes plan construction logic for different user-selected modes, ensuring consistent behavior.
        - 'basic' mode merges a predefined default plan with the base arguments.
        - 'advanced' mode currently uses only the base arguments.
        - 'auto' mode generates a plan via an LLM request, enriches it with workflow-specific actions, and ensures a requirements file is added if missing, providing an intelligent, context-aware starting point.
        - The PlanEditor confirmation step in 'auto' mode allows user review, increasing plan accuracy and user control.
        - Web interface compatibility is maintained by skipping confirmation when 'web_mode' is active for non-auto modes.
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
            logger.info(f"The following model is used to create the plan: {self.model_settings.model}.")
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

        return PlanEditor(self.workflow_manager.workflow_keys).confirm_action(plan)

    def _make_request_for_auto_mode(self) -> dict:
        """
        Send prompt to model and parse JSON response to build auto mode plan.
        
        This method constructs a prompt for the LLM using repository metadata, then sends the prompt and processes the response to produce a structured plan for the auto mode. The plan is validated and returned as a dictionary.
        
        WHY: The auto mode requires a structured plan from the LLM to guide subsequent documentation and enhancement operations. The method ensures the response is valid JSON and conforms to the expected schema, retrying on parsing or validation errors to improve reliability.
        
        Args:
            self: The ModeScheduler instance, which provides access to repository metadata, the model handler, and other necessary components.
        
        Returns:
            dict: The parsed and validated plan from the model response, converted from a Pydantic model to a dictionary.
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
