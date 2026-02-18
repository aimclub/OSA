import pytest

from osa_tool.config.settings import ConfigLoader


@pytest.fixture(scope="session")
def config_loader():
    """
    Loads and configures a ConfigLoader instance for testing.
    
    This fixture creates a ConfigLoader object, sets default Git configuration
    values for a test project, and returns the configured instance. The returned
    object can be used in tests that require a pre‑configured configuration.
    
    Parameters
    ----------
    None
    
    Returns
    -------
    ConfigLoader
        A ConfigLoader instance with its `config.git` attributes set to the
        following values:
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
