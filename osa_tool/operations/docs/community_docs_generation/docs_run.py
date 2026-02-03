from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.config.settings import ConfigManager
from osa_tool.operations.docs.community_docs_generation.community import CommunityTemplateBuilder
from osa_tool.operations.docs.community_docs_generation.contributing import ContributingBuilder
from osa_tool.operations.registry import Operation, OperationRegistry
from osa_tool.utils.logger import logger


def generate_documentation(config_manager: ConfigManager, metadata: RepositoryMetadata) -> bool:
    """
    This function initializes builders for various documentation templates such as
    contribution guidelines, community standards, and issue templates. It sequentially
    generates these files based on the loaded configuration.

    Args:
        config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
        metadata: Git repository metadata.

    Returns:
        Has the task been completed successfully
    """
    logger.info("Starting generating additional documentation.")

    contributing = ContributingBuilder(config_manager, metadata)
    contributing_result = contributing.build()

    community = CommunityTemplateBuilder(config_manager, metadata)
    code_of_conduct_result = community.build_code_of_conduct()
    security_result = community.build_security()
    pull_request_result = True
    bug_issue_result = True
    documentation_issue_result = True
    feature_issue_result = True
    vulnerability_disclosure_result = True

    if config_manager.get_git_settings().host in ["github", "gitlab"]:
        pull_request_result = community.build_pull_request()
        bug_issue_result = community.build_bug_issue()
        documentation_issue_result = community.build_documentation_issue()
        feature_issue_result = community.build_feature_issue()

    if config_manager.get_git_settings().host == "gitlab":
        vulnerability_disclosure_result = community.build_vulnerability_disclosure()

    logger.info("All additional documentation successfully generated.")
    return all(
        [
            contributing_result,
            code_of_conduct_result,
            security_result,
            pull_request_result,
            bug_issue_result,
            documentation_issue_result,
            feature_issue_result,
            vulnerability_disclosure_result,
        ]
    )


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
