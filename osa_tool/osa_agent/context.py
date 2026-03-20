from osa_tool.config.osa_config import OSAConfig
from osa_tool.core.llm.llm import ModelHandlerFactory


class AgentContext:
    """
    Shared execution context providing common data and coordination mechanisms for all processing agents.
    
        This object aggregates configuration, repository metadata,
        model handlers, and workflow-related utilities so that agents
        do not need to resolve or construct these dependencies themselves.
    """


    def __init__(self, agent_config: OSAConfig) -> None:
        """
        Initialize the context from the OSA configuration.
        
        Sets up the essential components and managers required for the agent's operation by extracting them from the provided OSA configuration. This includes the configuration itself, managers for workflows and prompts, the Git agent for repository interactions, and key operational flags.
        
        Args:
            agent_config: The OSA configuration object containing all necessary agents, managers, and settings.
        
        Why:
            The AgentContext serves as a central access point for the agent's runtime dependencies. This constructor centralizes the setup by pulling these dependencies from a single, validated configuration source (OSAConfig), ensuring consistency and simplifying dependency injection for the rest of the agent system.
        """
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
        
        This method retrieves the appropriate model configuration for the given task and builds a corresponding ModelHandler instance. It is used to ensure that each task (e.g., generating docstrings, creating READMEs, validation) can be processed with a model tailored to its specific requirements, optimizing performance and output quality.
        
        Args:
            task_type: Type of task (docstring, readme, validation, general). Defaults to "general".
        
        Returns:
            ModelHandler instance configured for the specified task. The configuration is obtained via the ConfigManager, which may return a default or task-specific setting based on the system's model‑usage mode.
        """
        model_settings = self.config_manager.get_model_settings(task_type)
        return ModelHandlerFactory.build(model_settings)
