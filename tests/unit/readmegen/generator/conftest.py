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


@pytest.fixture(autouse=True)
def mock_load_data_metadata():
    metadata_mock = MagicMock()
    metadata_mock.default_branch = "main"
    metadata_mock.license_name = "license_name"

    with (
        patch("osa_tool.readmegen.generator.base_builder.load_data_metadata", return_value=metadata_mock),
        patch("osa_tool.readmegen.generator.header.load_data_metadata", return_value=metadata_mock),
        patch("osa_tool.readmegen.generator.installation.load_data_metadata", return_value=metadata_mock),
    ):
        yield
