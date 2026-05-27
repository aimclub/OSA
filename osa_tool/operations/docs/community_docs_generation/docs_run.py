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
    contributing = ContributingBuilder(config_manager, metadata)
    community = CommunityTemplateBuilder(config_manager, metadata)

    try:
        contributing.build()
        events.append(OperationEvent(kind=EventKind.GENERATED, target="CONTRIBUTING"))
        generated_files.append("CONTRIBUTING.md")
    except Exception as e:
        logger.error("Failed to generate CONTRIBUTING: %s", repr(e), exc_info=True)
        events.append(OperationEvent(kind=EventKind.FAILED, target="CONTRIBUTING", data={"error": repr(e)}))

    try:
        community.build_code_of_conduct()
        events.append(OperationEvent(kind=EventKind.GENERATED, target="CODE_OF_CONDUCT"))
        generated_files.append("CODE_OF_CONDUCT.md")
    except Exception as e:
        logger.error("Failed to generate CODE_OF_CONDUCT: %s", repr(e), exc_info=True)
        events.append(OperationEvent(kind=EventKind.FAILED, target="CODE_OF_CONDUCT", data={"error": repr(e)}))

    try:
        community.build_security()
        events.append(OperationEvent(kind=EventKind.GENERATED, target="SECURITY"))
        generated_files.append("SECURITY.md")
    except Exception as e:
        logger.error("Failed to generate SECURITY: %s", repr(e), exc_info=True)
        events.append(OperationEvent(kind=EventKind.FAILED, target="SECURITY", data={"error": repr(e)}))

    if config_manager.get_git_settings().host in ["github", "gitlab"]:
        for method, target, filename in [
            (community.build_pull_request, "PULL_REQUEST_TEMPLATE", "PULL_REQUEST_TEMPLATE.md"),
            (community.build_bug_issue, "ISSUE_TEMPLATE:bug", "BUG_ISSUE.md"),
            (community.build_documentation_issue, "ISSUE_TEMPLATE:documentation", "DOCUMENTATION_ISSUE.md"),
            (community.build_feature_issue, "ISSUE_TEMPLATE:feature", "FEATURE_ISSUE.md"),
        ]:
            try:
                method()
                events.append(OperationEvent(kind=EventKind.GENERATED, target=target))
                generated_files.append(filename)
            except Exception as e:
                logger.error("Failed to generate %s: %s", target, repr(e), exc_info=True)
                events.append(OperationEvent(kind=EventKind.FAILED, target=target, data={"error": repr(e)}))

    if config_manager.get_git_settings().host == "gitlab":
        try:
            community.build_vulnerability_disclosure()
            events.append(OperationEvent(kind=EventKind.GENERATED, target="VULNERABILITY_DISCLOSURE"))
            generated_files.append("Vulnerability_Disclosure.md")
        except Exception as e:
            logger.error("Failed to generate VULNERABILITY_DISCLOSURE: %s", repr(e), exc_info=True)
            events.append(
                OperationEvent(kind=EventKind.FAILED, target="VULNERABILITY_DISCLOSURE", data={"error": repr(e)})
            )

    logger.info("Additional documentation generation completed.")

    return {
        "result": {
            "generated": generated_files,
        },
        "events": events,
    }
