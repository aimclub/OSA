from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_args_basic(workflow_keys):
    """
    Creates a mock arguments object with basic configuration and dynamic workflow attributes.
    This is used primarily for testing to simulate command-line arguments or configuration objects without requiring actual argument parsing.
    
    Args:
        workflow_keys: A list of strings representing specific workflow attributes to be enabled on the mock object. Each key becomes an attribute on the mock object set to True.
    
    Returns:
        MagicMock: A mock object configured with basic mode settings and the specified workflow keys set to True. The mock will have `mode` set to "basic" and `web_mode` set to False by default.
    """
    args = MagicMock()
    args.mode = "basic"
    args.web_mode = False

    for key in workflow_keys:
        setattr(args, key, True)
    return args


@pytest.fixture
def mock_args_advanced(workflow_keys):
    """
    Creates a mock arguments object configured for advanced mode with dynamic workflow attributes.
    
    This function is used in testing to simulate a command-line arguments object where the tool is set to 'advanced' mode (non-web interface) and specific workflow-related flags are disabled (set to False). This allows isolated testing of components that depend on these configuration settings.
    
    Args:
        workflow_keys: A collection of strings representing specific workflow keys to be initialized as attributes on the mock object. Each key will be added as an attribute with a value of False.
    
    Returns:
        MagicMock: A mock object with 'mode' set to 'advanced', 'web_mode' set to False, and each key in workflow_keys initialized to False.
    """
    args = MagicMock()
    args.mode = "advanced"
    args.web_mode = False
    for key in workflow_keys:
        setattr(args, key, False)
    return args


@pytest.fixture
def mock_args_auto(workflow_keys):
    """
    Creates a mock arguments object configured for automatic mode.
    
    This function is used primarily in testing to simulate a command-line arguments object where the tool is set to run automatically (non-interactively) and not in a web interface mode. It allows specific workflow flags to be enabled for testing different operational scenarios.
    
    Args:
        workflow_keys: A collection of keys (strings) representing specific workflows to be enabled on the mock object. Each key will be set as an attribute on the mock with a value of True.
    
    Returns:
        MagicMock: A mock object with 'mode' set to 'auto', 'web_mode' set to False, and all specified workflow keys set to True as attributes.
    """
    args = MagicMock()
    args.mode = "auto"
    args.web_mode = False
    for key in workflow_keys:
        setattr(args, key, True)
    return args


@pytest.fixture
def mock_workflow_manager():
    """
    Creates a mocked WorkflowManager instance for testing purposes.
    
    This function returns a MagicMock object configured with predefined workflow keys and a fixed return value for the `build_actual_plan` method. It is used to simulate a WorkflowManager in unit tests without requiring the actual implementation or external dependencies.
    
    Args:
        None
    
    Returns:
        A MagicMock object representing a WorkflowManager, with the following attributes set:
            - workflow_keys: A list of string identifiers for available workflow operations.
            - build_actual_plan.return_value: A dictionary representing a sample workflow plan, mapping workflow keys to example values.
    """
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
