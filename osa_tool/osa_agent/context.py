from osa_tool.config.osa_config import OSAConfig
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory


class AgentContext:
    """
    Shared execution context passed to all agents.

    This object aggregates configuration, repository metadata,
    model handlers, and workflow-related utilities so that agents
    do not need to resolve or construct these dependencies themselves.
    """

    def __init__(self, agent_config: OSAConfig):
        self.agent_config = agent_config
        self.config_manager = self.agent_config.config_manager
        self.git_agent = self.agent_config.git_agent
        self.metadata = self.git_agent.metadata
        self.model_handler_factory = ModelHandlerFactory
        self.workflow_manager = self.agent_config.workflow_manager
        self.prompts = self.config_manager.get_prompts()
        self.create_fork = self.agent_config.create_fork
        self.create_pull_request = self.agent_config.create_pull_request
        self.delete_repo = self.agent_config.delete_dir

    def get_model_handler(self, task_type: str = "general"):
        """
        Get a model handler configured for a specific task type.

        Args:
            task_type: Type of task (docstring, readme, validation, general)

        Returns:
            ModelHandler instance configured for the specified task
        """
        model_settings = self.config_manager.get_model_settings(task_type)
        return ModelHandlerFactory.build(model_settings)
