from unittest.mock import patch, MagicMock

import pytest

from osa_tool.readmegen.generator.builder import MarkdownBuilder
from osa_tool.readmegen.generator.builder_article import MarkdownBuilderArticle
from osa_tool.readmegen.generator.header import HeaderBuilder
from osa_tool.readmegen.generator.installation import InstallationSectionBuilder
from tests.utils.fixtures.analytics_sourcerank import sourcerank_with_repo_tree
from tests.utils.mocks.repo_trees import get_mock_repo_tree


@pytest.fixture
def mock_markdown_builder(
    mock_config_loader, load_metadata_base_builder, load_metadata_header, load_metadata_installation
):
    def _create_builder(core_features=None, overview=None, getting_started=None):
        builder = MarkdownBuilder(
            config_loader=mock_config_loader,
            core_features=core_features,
            overview=overview,
            getting_started=getting_started,
        )
        return builder

    return _create_builder


@pytest.fixture
def mock_markdown_builder_article(
    mock_config_loader, load_metadata_base_builder, load_metadata_header, load_metadata_installation
):
    def _create_builder(overview=None, content=None, algorithms=None, getting_started=None):
        builder = MarkdownBuilderArticle(
            config_loader=mock_config_loader,
            overview=overview,
            content=content,
            algorithms=algorithms,
            getting_started=getting_started,
        )
        return builder

    return _create_builder


@pytest.fixture
def mock_pypi_inspector():
    with patch("osa_tool.readmegen.generator.header.PyPiPackageInspector") as mock_inspector:
        mock_instance = MagicMock()
        mock_instance.get_info.return_value = {"name": "test-package", "version": "1.0.0", "downloads": 1000}
        mock_inspector.return_value = mock_instance
        yield mock_inspector


@pytest.fixture
def mock_dependency_extractor():
    with patch("osa_tool.readmegen.generator.header.DependencyExtractor") as mock_extractor:
        mock_instance = MagicMock()
        mock_instance.extract_techs.return_value = {"python", "numpy"}
        mock_extractor.return_value = mock_instance
        yield mock_extractor


@pytest.fixture
def mock_header_builder(
    mock_config_loader, load_metadata_header, mock_pypi_inspector, mock_dependency_extractor, sourcerank_with_repo_tree
):
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder = HeaderBuilder(mock_config_loader)
    builder.tree = sourcerank.tree
    return builder


@pytest.fixture
def mock_installation_builder(
    mock_config_loader,
    load_metadata_installation,
    mock_pypi_inspector,
    mock_dependency_extractor,
    sourcerank_with_repo_tree,
):
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder = InstallationSectionBuilder(mock_config_loader)
    builder.sourcerank = sourcerank
    return builder
