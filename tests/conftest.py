from contextlib import ExitStack
from unittest.mock import Mock, patch, MagicMock

import pytest

from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import Settings, GitSettings, ModelSettings, WorkflowSettings
from osa_tool.utils import parse_folder_name
from tests.data_factory import DataFactory


@pytest.fixture(scope="session")
def data_factory():
    return DataFactory()


# -------------------
# Config Loader Fixtures
# -------------------
@pytest.fixture
def mock_config_loader(data_factory):
    """Mock ConfigLoader with dynamically generated test data"""
    test_settings = data_factory.generate_full_settings()
    # Create real Pydantic models from generated data
    settings = Settings(
        git=GitSettings(**test_settings["git"]),
        llm=ModelSettings(**test_settings["llm"]),
        workflows=WorkflowSettings(**test_settings["workflows"]),
    )

    # Create mock loader
    mock_loader = Mock()
    mock_loader.config = settings

    # Patch the original ConfigLoader
    with (patch("osa_tool.config.settings.ConfigLoader", return_value=mock_loader),):
        yield mock_loader


@pytest.fixture
def config_loader_with_updates(mock_config_loader):
    """Fixture for tests that need to modify config"""

    def updater(**kwargs):
        for section, values in kwargs.items():
            if hasattr(mock_config_loader.config, section):
                current = getattr(mock_config_loader.config, section).dict()
                updated = {**current, **values}
                setattr(
                    mock_config_loader.config, section, type(getattr(mock_config_loader.config, section))(**updated)
                )
        return mock_config_loader

    return updater


# -------------------
# SourceRank Fixtures
# -------------------
@pytest.fixture
def mock_sourcerank(mock_config_loader, mock_parse_folder_name, data_factory):
    """Factory fixture to create SourceRank instances with patched methods."""

    def factory(repo_tree=None, method_overrides=None) -> SourceRank:
        overrides = method_overrides or {}
        random_methods = data_factory.random_source_rank_methods(force_overrides=overrides)

        patches = [
            patch("osa_tool.analytics.sourcerank.parse_folder_name", return_value=mock_parse_folder_name),
        ]

        if repo_tree is not None:
            patches.append(patch("osa_tool.analytics.sourcerank.get_repo_tree", return_value=repo_tree))

        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)

            instance = SourceRank(mock_config_loader)

            # Explicitly patch methods on the instance using MagicMock
            for method_name, return_value in random_methods.items():
                mocked_method = MagicMock(return_value=return_value)
                setattr(instance, method_name, mocked_method)

            # Yielding the fully prepared instance
            return instance

    return factory


@pytest.fixture
def mock_parse_folder_name(mock_config_loader):
    repo_url = mock_config_loader.config.git.repository
    return parse_folder_name(repo_url)
