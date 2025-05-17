from osa_tool.config.settings import ConfigLoader
from osa_tool.docs_generator.community import CommunityTemplateBuilder
from osa_tool.docs_generator.contributing import ContributingBuilder
from osa_tool.utils import logger


def generate_documentation(config_loader: ConfigLoader) -> None:
    """
    This function initializes builders for various documentation templates such as
    contribution guidelines, community standards, and issue templates. It sequentially
    generates these files based on the loaded configuration.

    Args:
        config_loader: The configuration object which contains settings for osa_tool.

    Returns:
        None
    """
    logger.info("Starting generating additional documentation.")

    contributing = ContributingBuilder(config_loader)
    contributing.build()

    community = CommunityTemplateBuilder(config_loader)
    community.build_code_of_conduct()
    community.build_pull_request()
    community.build_bug_issue()
    community.build_documentation_issue()
    community.build_feature_issue()

    logger.info("All additional documentation successfully generated.")
