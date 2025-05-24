from unittest.mock import Mock

import pytest

from osa_tool.aboutgen.about_generator import AboutGenerator
from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.config.settings import ConfigLoader


@pytest.fixture
def mock_config():
    config = Mock()
    config.git.repository = "https://github.com/test/repo"
    return config


@pytest.fixture
def mock_config_loader(mock_config):
    loader = Mock(spec=ConfigLoader)
    loader.config = mock_config
    return loader


@pytest.fixture
def mock_metadata():
    metadata = Mock(spec=RepositoryMetadata)
    metadata.description = None
    metadata.homepage_url = None
    metadata.topics = []
    metadata.default_branch = "main"
    return metadata


@pytest.fixture
def sample_readme_content():
    return """
    # Test Project
    
    This is a test project that does amazing things.
    Check out our [documentation](https://docs.test-project.com).
    Visit our [homepage](https://test-project.com).
    """


@pytest.fixture
def about_generator(mock_config_loader, mocker):
    mocker.patch("osa_tool.aboutgen.about_generator.load_data_metadata")
    mocker.patch("osa_tool.aboutgen.about_generator.extract_readme_content")
    mocker.patch("osa_tool.aboutgen.about_generator.ModelHandlerFactory.build")
    return AboutGenerator(mock_config_loader)
