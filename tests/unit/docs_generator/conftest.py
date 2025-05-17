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
