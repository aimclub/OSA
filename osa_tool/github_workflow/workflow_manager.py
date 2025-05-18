import os

from osa_tool.config.settings import ConfigLoader
from osa_tool.github_workflow import generate_workflows_from_settings
from osa_tool.utils import parse_folder_name, logger


def update_workflow_config(config_loader, workflow_settings: dict) -> None:
    config_loader.config.workflows = config_loader.config.workflows.model_copy(update=workflow_settings)
    logger.info("Config successfully updated with workflow_settings")


def generate_github_workflows(config_loader: ConfigLoader) -> None:
    """
    Generate GitHub Action workflows based on configuration settings.
    Args:
        config_loader: Configuration loader object which contains workflow settings
    """
    try:
        logger.info("Generating GitHub action workflows...")

        # Get the workflow settings from the config
        workflow_settings = config_loader.config.workflows
        repo_url = config_loader.config.git.repository
        output_dir = os.path.join(os.getcwd(), parse_folder_name(
            repo_url), workflow_settings.output_dir)

        created_files = generate_workflows_from_settings(
            workflow_settings, output_dir)

        if created_files:
            formatted_files = "\n".join(f" - {file}" for file in created_files)
            logger.info("Successfully generated the following workflow files:\n%s", formatted_files)
        else:
            logger.info("No workflow files were generated.")

    except Exception as e:
        logger.error("Error while generating GitHub workflows: %s",
                     repr(e), exc_info=True)