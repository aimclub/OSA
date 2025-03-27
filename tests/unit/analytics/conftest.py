import pytest

from pathlib import Path
from unittest.mock import MagicMock, patch

from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.analytics.report_generator import TextGenerator


@pytest.fixture
def config_loader():
    mock_loader = MagicMock()
    mock_loader.config.git.repository = "https://github.com/testuser/testrepo.git"
    mock_loader.repo_path = Path("/mock/path/repo")
    return mock_loader


@pytest.fixture
@patch("osa_tool.analytics.metadata.load_data_metadata", return_value={})
@patch("osa_tool.utils.osa_project_root", return_value="/mock/path")
@patch("osa_tool.utils.parse_folder_name", return_value="testrepo")
@patch("osa_tool.analytics.sourcerank.ingest", return_value=(None, "README.md LICENSE tests", None))
def source_rank(
        mock_ingest,
        mock_parse,
        mock_project_root,
        mock_metadata,
        config_loader
):
    return SourceRank(config_loader)


@pytest.fixture()
@patch("osa_tool.osatreesitter.models.ModelHandlerFactory.build", autospec=True)
@patch("osa_tool.analytics.metadata.load_data_metadata", autospec=True)
@patch("osa_tool.analytics.sourcerank.ingest", return_value=(None, "README.md LICENSE tests", None))
def text_generator(
        mock_ingest,
        mock_load_data_metadata,
        mock_model_handler_factory,
        source_rank,
        config_loader
):
    mock_load_data_metadata.return_value = {
        "name": "testrepo",
        "description": "Test repository"
    }

    return TextGenerator(config_loader)
