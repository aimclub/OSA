from unittest.mock import patch

import pytest

from osa_tool.ui.plan_editor import PlanEditor


@pytest.fixture
def workflow_keys():
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
    with patch("osa_tool.ui.plan_editor.read_arguments_file_flat", return_value={}):
        editor = PlanEditor(workflow_keys)
    return editor
