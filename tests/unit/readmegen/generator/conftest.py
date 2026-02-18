from unittest.mock import patch, MagicMock

import pytest

from osa_tool.config.settings import ConfigLoader


@pytest.fixture(scope="session")
def config_loader():
    """
    Loads and returns a ConfigLoader instance with predefined git configuration.
    
    This fixture creates a `ConfigLoader` object, sets its `git` configuration
    attributes to default values for a test project, and returns the instance
    for use in tests.
    
    Parameters
    ----------
    None
    
    Returns
    -------
    ConfigLoader
        A `ConfigLoader` instance with the following git configuration set:
        - name: "TestProject"
        - repository: "https://github.com/user/TestProject"
        - host: "github"
        - full_name: "user/TestProject"
    """
    config_loader = ConfigLoader()
    config_loader.config.git.name = "TestProject"
    config_loader.config.git.repository = "https://github.com/user/TestProject"
    config_loader.config.git.host = "github"
    config_loader.config.git.full_name = "user/TestProject"
    return config_loader


@pytest.fixture
def mock_load_data_metadata():
    """
    Mock load_data_metadata for tests.
    
    This fixture patches the `load_data_metadata` function in both the
    `osa_tool.readmegen.generator.base_builder` and
    `osa_tool.readmegen.generator.header` modules to return a
    `MagicMock` object with predefined attributes. The mock object
    provides a `default_branch` set to ``"main"`` and a
    `license_name` set to ``"license_name"``. After yielding control to
    the test, the patches are stopped to restore the original functions.
    
    Parameters:
        None
    
    Yields:
        None
    
    Returns:
        None
    """
    metadata_mock = MagicMock()
    metadata_mock.default_branch = "main"
    metadata_mock.license_name = "license_name"

    patcher_builder = patch("osa_tool.readmegen.generator.base_builder.load_data_metadata", return_value=metadata_mock)
    patcher_header = patch("osa_tool.readmegen.generator.header.load_data_metadata", return_value=metadata_mock)

    mock_builder = patcher_builder.start()
    mock_header = patcher_header.start()

    yield

    patcher_builder.stop()
    patcher_header.stop()
