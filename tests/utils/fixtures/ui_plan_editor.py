from unittest.mock import patch

import pytest

from osa_tool.ui.plan_editor import PlanEditor


@pytest.fixture
def workflow_keys():
    """
    Returns a list of available workflow configuration keys.
    
    These keys are used to enable or disable specific automated tasks within the OSA Tool's workflow generation system. Each key corresponds to a particular operation, such as code linting, testing, formatting, or publishing, allowing users to customize which tasks are included in their generated workflows.
    
    Returns:
        list: A list of strings representing the supported workflow options. The current keys are:
            - "include_black": Enables Black code formatting.
            - "include_tests": Enables test execution.
            - "include_pep8": Enables PEP8 style checking.
            - "include_autopep8": Enables automatic PEP8 correction via autopep8.
            - "include_fix_pep8": Enables manual PEP8 fixing.
            - "slash_command_dispatch": Enables slash command handling for workflow triggers.
            - "pypi_publish": Enables automated publishing to PyPI.
            - "generate_workflows": Enables the generation of workflow files themselves.
    """
    return [
        "include_black",
        "include_tests",
        "include_pep8",
        "include_autopep8",
        "include_fix_pep8",
        "slash_command_dispatch",
        "pypi_publish",
        "generate_workflows",
    ]


@pytest.fixture
def sample_plan():
    """
    Generates a sample configuration plan for repository processing.
    This plan serves as a default template or example, illustrating the structure and keys expected by the OSA Tool's processing pipeline. It is useful for understanding the configuration format and for initial setup.
    
    Returns:
        dict: A dictionary containing default configuration settings. Includes:
            - Repository information (URL, API type, processing mode).
            - General actions to perform (e.g., process README, docstrings, notebooks).
            - Workflow preferences (e.g., include Black formatting, PEP8 checks, test generation).
            - Miscellaneous other settings.
    """
    return {
        # Info keys
        "repository": "https://github.com/test/repo",
        "mode": "auto",
        "web_mode": False,
        "api": "github",
        # General actions
        "about": True,
        "readme": True,
        "docstring": False,
        "convert_notebooks": None,
        # Workflow keys
        "include_black": True,
        "include_tests": False,
        "include_pep8": True,
        "generate_workflows": True,
        # No workflow_keys
        "some_other_action": "some_value",
    }


@pytest.fixture
def plan_editor(workflow_keys):
    """
    Initializes and returns a PlanEditor instance with mocked argument reading.
    
    This method patches the argument reading utility to return an empty dictionary before instantiating the PlanEditor with the provided workflow keys. This is done to isolate the PlanEditor from external argument files during testing or specific runtime scenarios, ensuring consistent behavior regardless of any existing argument files.
    
    Args:
        workflow_keys: The keys identifying the workflows to be loaded into the editor.
    
    Returns:
        PlanEditor: An initialized instance of the PlanEditor class.
    """
    with patch("osa_tool.ui.plan_editor.read_arguments_file_flat", return_value={}):
        editor = PlanEditor(workflow_keys)
    return editor
