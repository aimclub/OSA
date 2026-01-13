from osa_tool.config.osa_config import OSAConfig
from osa_tool.models.models import ModelHandler, ModelHandlerFactory


class AgentContext:
    def __init__(self, agent_config: OSAConfig):
        self.agent_config = agent_config
        self.config_loader = self.agent_config.config_loader
        self.git_agent = self.agent_config.git_agent
        self.metadata = self.git_agent.metadata
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config_loader.config)
        self.workflow_manager = self.agent_config.workflow_manager
        self.prompts = self.config_loader.config.prompts
        self.create_fork = self.agent_config.create_fork
        self.create_pull_request = self.agent_config.create_pull_request
