from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.models.event import OperationEvent, EventKind
from osa_tool.operations.docs.community_docs_generation.community import CommunityTemplateBuilder
from osa_tool.operations.docs.community_docs_generation.contributing import ContributingBuilder
from osa_tool.utils.logger import logger


def generate_documentation(config_manager: ConfigManager, metadata: RepositoryMetadata) -> dict:
    """
    This function initializes builders for various documentation templates such as
    contribution guidelines, community standards, and issue templates. It sequentially
    generates these files based on the loaded configuration.

    Args:
        config_manager: A unified configuration manager that provides task-specific LLM settings, repository information, and workflow preferences.
        metadata: Git repository metadata.

    Returns:
        dict: Standardized operation output containing:
            - result: Generated documentation summary
            - events: List of OperationEvent
    """
    logger.info("Starting generating additional documentation.")

    events: list[OperationEvent] = []
    generated_files: list[str] = []
    # TODO: Добавить план
    contributing = ContributingBuilder(config_manager, metadata)
    contributing.build()
    events.append(OperationEvent(kind=EventKind.GENERATED, target="CONTRIBUTING"))
    generated_files.append("CONTRIBUTING.md")

    community = CommunityTemplateBuilder(config_manager, metadata)
    community.build_code_of_conduct()
    events.append(OperationEvent(kind=EventKind.GENERATED, target="CODE_OF_CONDUCT"))
    generated_files.append("CODE_OF_CONDUCT.md")

    community.build_security()
    events.append(OperationEvent(kind=EventKind.GENERATED, target="SECURITY"))
    generated_files.append("SECURITY.md")

    if config_manager.get_git_settings().host in ["github", "gitlab"]:
        community.build_pull_request()
        community.build_bug_issue()
        community.build_documentation_issue()
        community.build_feature_issue()

        events.extend(
            [
                OperationEvent(kind=EventKind.GENERATED, target="PULL_REQUEST_TEMPLATE"),
                OperationEvent(kind=EventKind.GENERATED, target="ISSUE_TEMPLATE:bug"),
                OperationEvent(kind=EventKind.GENERATED, target="ISSUE_TEMPLATE:documentation"),
                OperationEvent(kind=EventKind.GENERATED, target="ISSUE_TEMPLATE:feature"),
            ]
        )
        generated_files.extend(
            [
                "PULL_REQUEST_TEMPLATE.md",
                "BUG_ISSUE.md",
                "DOCUMENTATION_ISSUE.md",
                "FEATURE_ISSUE.md",
            ]
        )

    if config_manager.get_git_settings().host == "gitlab":
        community.build_vulnerability_disclosure()

        events.append(
            OperationEvent(
                kind=EventKind.GENERATED,
                target="VULNERABILITY_DISCLOSURE",
            )
        )
        generated_files.append("Vulnerability_Disclosure.md")

    logger.info("All additional documentation successfully generated.")

    return {
        "result": {
            "generated": generated_files,
        },
        "events": events,
    }
