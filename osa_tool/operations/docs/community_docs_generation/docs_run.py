from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.config.settings import ConfigManager
from osa_tool.operations.docs.community_docs_generation.community import CommunityTemplateBuilder
from osa_tool.operations.docs.community_docs_generation.contributing import ContributingBuilder
from osa_tool.operations.registry import Operation, OperationRegistry
from osa_tool.utils.logger import logger


def generate_documentation(config_manager: ConfigManager, metadata: RepositoryMetadata) -> None:
    """
    This function initializes builders for various documentation templates such as
    contribution guidelines, community standards, and issue templates. It sequentially
    generates these files based on the loaded configuration.

    Args:
        config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
        metadata: Git repository metadata.

    Returns:
        None
    """
    logger.info("Starting generating additional documentation.")

    contributing = ContributingBuilder(config_manager, metadata)
    contributing.build()

    community = CommunityTemplateBuilder(config_manager, metadata)
    community.build_code_of_conduct()
    community.build_security()

    if config_manager.get_git_settings().host in ["github", "gitlab"]:
        community.build_pull_request()
        community.build_bug_issue()
        community.build_documentation_issue()
        community.build_feature_issue()

    if config_manager.get_git_settings().host == "gitlab":
        community.build_vulnerability_disclosure()

    logger.info("All additional documentation successfully generated.")


class GenerateCommunityDocsOperation(Operation):
    name = "generate_documentation"
    description = "Generate additional documentation files (e.g., CONTRIBUTING, CODE_OF_CONDUCT)."

    supported_intents = ["new_task"]
    supported_scopes = ["full_repo", "docs"]
    priority = 65

    executor = staticmethod(generate_documentation)
    executor_method = None
    executor_dependencies = ["config_manager", "metadata"]


OperationRegistry.register(GenerateCommunityDocsOperation())
