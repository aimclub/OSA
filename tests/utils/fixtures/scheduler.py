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
def workflow_keys():
    return [
        "include_black",
        "include_tests",
        "include_pep8",
        "include_autopep8",
        "include_fix_pep8",
        "slash_command_dispatch",
        "pypi_publish",
    ]
