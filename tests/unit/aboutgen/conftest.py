from unittest.mock import Mock

import pytest

from osa_tool.aboutgen.about_generator import AboutGenerator
from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.config.settings import ConfigLoader


@pytest.fixture
def mock_config():
    """
    Creates a mock configuration object for testing purposes.
    
    This function constructs a Mock instance and assigns a predefined Git
    repository URL to the `git.repository` attribute. The resulting mock
    object can be used in tests that expect a configuration object with
    a `git.repository` property.
    
    Returns:
        Mock: A mock configuration object with `git.repository` set to
        "https://github.com/test/repo".
    """
    config = Mock()
    config.git.repository = "https://github.com/test/repo"
    return config


@pytest.fixture
def mock_config_loader(mock_config):
    """
    Create a mock ConfigLoader instance with a predefined configuration.
    
    Args:
        mock_config: The configuration object to assign to the mock loader.
    
    Returns:
        A Mock instance of ConfigLoader with its `config` attribute set to `mock_config`.
    """
    loader = Mock(spec=ConfigLoader)
    loader.config = mock_config
    return loader


@pytest.fixture
def mock_metadata():
    """
    Creates a mock RepositoryMetadata object with default values.
    
    This helper function constructs a mock instance of `RepositoryMetadata` using
    `unittest.mock.Mock`. The mock is configured with a set of attributes that
    represent typical metadata for a repository. The attributes are set to
    reasonable defaults: `description` and `homepage_url` are `None`, `topics`
    is an empty list, and `default_branch` is `"main"`.
    
    Args:
        None
    
    Returns:
        Mock: A mock object mimicking `RepositoryMetadata` with the following
        attributes initialized:
            description: None
            homepage_url: None
            topics: []
            default_branch: "main"
    """
    metadata = Mock(spec=RepositoryMetadata)
    metadata.description = None
    metadata.homepage_url = None
    metadata.topics = []
    metadata.default_branch = "main"
    return metadata


@pytest.fixture
def sample_readme_content():
    """
    Generate a sample README content for a test project.
    
    Returns:
        str: A Markdown-formatted string containing a project title, description, and links to documentation and homepage.
    """
    return """
    # Test Project
    
    This is a test project that does amazing things.
    Check out our [documentation](https://docs.test-project.com).
    Visit our [homepage](https://test-project.com).
    """


@pytest.fixture
def about_generator(mock_config_loader, mocker):
    """
    Create an AboutGenerator instance with patched dependencies for testing.
    
    This helper patches internal functions used by `AboutGenerator` so that
    unit tests can run without relying on external data or side effects.
    
    Parameters
    ----------
    mock_config_loader
        A mock configuration loader used to instantiate the AboutGenerator.
    mocker
        A pytest-mock mocker fixture used to patch internal functions.
    
    Returns
    -------
    AboutGenerator
        An AboutGenerator instance with `load_data_metadata`, `extract_readme_content`,
        and `ModelHandlerFactory.build` patched to avoid external side effects.
    """
    mocker.patch("osa_tool.aboutgen.about_generator.load_data_metadata")
    mocker.patch("osa_tool.aboutgen.about_generator.extract_readme_content")
    mocker.patch("osa_tool.aboutgen.about_generator.ModelHandlerFactory.build")
    return AboutGenerator(mock_config_loader)
