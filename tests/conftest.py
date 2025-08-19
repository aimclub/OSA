from contextlib import ExitStack
from unittest.mock import Mock, patch, MagicMock

import pytest

from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import Settings, GitSettings, ModelSettings, WorkflowSettings
from osa_tool.utils import parse_folder_name
from tests.data_factory import DataFactory
from tests.utils.mocks.requests_mock import mock_requests_response


@pytest.fixture(scope="session")
def data_factory():
    return DataFactory()


# -------------------
# Config Loader Fixtures
# -------------------
@pytest.fixture
def mock_config_loader(data_factory, request):
    """Mock ConfigLoader with dynamically generated test data"""
    platform = getattr(request, "param", "github")
    test_settings = data_factory.generate_full_settings(platform)
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


# -------------------
# RepositoryMetadata Fixtures
# -------------------
@pytest.fixture
def repo_info(mock_config_loader):
    full_name = mock_config_loader.config.git.full_name
    owner, repo_name = full_name.split("/")
    repo_url = mock_config_loader.config.git.repository
    platform = mock_config_loader.config.git.host
    return platform, owner, repo_name, repo_url


@pytest.fixture
def mock_requests_response_factory():
    """Fixture to provide a reusable mock response factory for requests.get."""
    return mock_requests_response


@pytest.fixture
def mock_repository_metadata(data_factory, repo_info):
    platform, owner, repo_name, repo_url = repo_info
    return data_factory.generate_repository_metadata(platform, owner, repo_name, repo_url)


def create_load_metadata_fixture(target_path: str):
    @pytest.fixture
    def _fixture(mock_repository_metadata):
        with patch(target_path, return_value=mock_repository_metadata) as mock_func:
            yield mock_func

    return _fixture


# aboutgen module
load_metadata_about_generator = create_load_metadata_fixture("osa_tool.aboutgen.about_generator.load_data_metadata")
# analytics module
load_metadata_report_maker = create_load_metadata_fixture("osa_tool.analytics.report_maker.load_data_metadata")
load_metadata_report_generator = create_load_metadata_fixture("osa_tool.analytics.report_generator.load_data_metadata")
# docs_generator module
load_metadata_community = create_load_metadata_fixture("osa_tool.docs_generator.community.load_data_metadata")
load_metadata_contributing = create_load_metadata_fixture("osa_tool.docs_generator.contributing.load_data_metadata")
load_metadata_license = create_load_metadata_fixture("osa_tool.docs_generator.license.load_data_metadata")
# readmegen/generator
load_metadata_base_builder = create_load_metadata_fixture(
    "osa_tool.readmegen.generator.base_builder.load_data_metadata"
)
load_metadata_header = create_load_metadata_fixture("osa_tool.readmegen.generator.header.load_data_metadata")
load_metadata_installation = create_load_metadata_fixture(
    "osa_tool.readmegen.generator.installation.load_data_metadata"
)


@pytest.fixture
def mock_parse_folder_name(mock_config_loader):
    repo_url = mock_config_loader.config.git.repository
    return parse_folder_name(repo_url)
