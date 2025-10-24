from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_args_basic(workflow_keys):
    args = MagicMock()
    args.mode = "basic"
    args.web_mode = False

    for key in workflow_keys:
        setattr(args, key, True)
    return args


@pytest.fixture
def mock_args_advanced(workflow_keys):
    args = MagicMock()
    args.mode = "advanced"
    args.web_mode = False
    for key in workflow_keys:
        setattr(args, key, False)
    return args


@pytest.fixture
def mock_args_auto(workflow_keys):
    args = MagicMock()
    args.mode = "auto"
    args.web_mode = False
    for key in workflow_keys:
        setattr(args, key, True)
    return args


@pytest.fixture
def mock_workflow_manager():
    """Mock WorkflowManager instance."""
    workflow_manager = MagicMock()
    workflow_manager.workflow_keys = [
        "include_black",
        "include_tests",
        "include_pep8",
        "include_autopep8",
        "include_fix_pep8",
        "slash_command_dispatch",
        "pypi_publish",
        "python_versions",
    ]
    workflow_manager.build_actual_plan.return_value = {
        "include_tests": True,
        "include_black": False,
        "python_versions": ["3.10"],
    }
    return workflow_manager
