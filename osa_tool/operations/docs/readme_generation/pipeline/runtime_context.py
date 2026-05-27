"""Shared dependency-injection container passed to every README generation node."""

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.llm.llm import ModelHandler, ModelHandlerFactory


class ReadmeContext:
    """Shared dependencies for all README generation nodes."""

    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata) -> None:
        self.config_manager = config_manager
        self.metadata = metadata
        self.prompts = config_manager.get_prompts()
        self.model_handler: ModelHandler = ModelHandlerFactory.build(config_manager.get_model_settings("readme"))
