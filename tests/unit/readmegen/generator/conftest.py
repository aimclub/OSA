from unittest.mock import patch, MagicMock

import pytest

from osa_tool.config.settings import ConfigLoader


@pytest.fixture(scope="session")
def config_loader():
    config_loader = ConfigLoader()
    config_loader.config.git.name = "TestProject"
    config_loader.config.git.repository = "https://github.com/user/TestProject"
    config_loader.config.git.host = "github"
    config_loader.config.git.full_name = "user/TestProject"
    return config_loader


@pytest.fixture
def mock_load_data_metadata():
    metadata_mock = MagicMock()
    metadata_mock.default_branch = "main"
    metadata_mock.license_name = "license_name"

    patcher_builder = patch("osa_tool.readmegen.generator.builder.load_data_metadata", return_value=metadata_mock)
    patcher_header = patch("osa_tool.readmegen.generator.header.load_data_metadata", return_value=metadata_mock)

    mock_builder = patcher_builder.start()
    mock_header = patcher_header.start()

    yield

    patcher_builder.stop()
    patcher_header.stop()
