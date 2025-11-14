from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.config.settings import ConfigLoader
from osa_tool.docs_generator.community import CommunityTemplateBuilder
from osa_tool.docs_generator.contributing import ContributingBuilder
from osa_tool.utils.logger import logger


def generate_documentation(config_loader: ConfigLoader, metadata: RepositoryMetadata) -> None:
    """
    This function initializes builders for various documentation templates such as
    contribution guidelines, community standards, and issue templates. It sequentially
    generates these files based on the loaded configuration.

    Args:
        config_loader: The configuration object which contains settings for osa_tool.
        metadata: Git repository metadata.

    Returns:
        None
    """
    logger.info("Starting generating additional documentation.")

    contributing = ContributingBuilder(config_loader, metadata)
    contributing.build()

    community = CommunityTemplateBuilder(config_loader, metadata)
    community.build_code_of_conduct()
    community.build_pull_request()
    community.build_bug_issue()
    community.build_documentation_issue()
    community.build_feature_issue()
    community.build_security()

    if config_loader.config.git.host == "gitlab":
        community.build_vulnerability_disclosure()

    logger.info("All additional documentation successfully generated.")
