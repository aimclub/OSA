import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from osa_tool.analytics.prompt_builder import RepositoryReport, YesNoPartial
from osa_tool.analytics.report_generator import TextGenerator
from osa_tool.analytics.report_maker import ReportGenerator
from osa_tool.analytics.sourcerank import SourceRank


@pytest.fixture
def mock_config_loader():
    """Returns a mocked config loader with a test repository path."""
    mock_loader = MagicMock()
    mock_config = MagicMock()
    mock_config.git.repository = "https://github.com/testuser/testrepo.git"
    mock_loader.repo_path = Path("/mock/path/repo")
    mock_loader.config = mock_config
    return mock_loader


@pytest.fixture
@patch("osa_tool.analytics.metadata.load_data_metadata", return_value={})
@patch("osa_tool.utils.osa_project_root", return_value="/mock/path")
@patch("osa_tool.utils.parse_folder_name", return_value="testrepo")
@patch("osa_tool.utils.get_repo_tree", return_value=(None, "README.md LICENSE tests", None))
def source_rank(mock_ingest, mock_parse, mock_project_root, mock_metadata, mock_config_loader):
    """Returns a mocked SourceRank instance with pre-defined repository structure."""
    return SourceRank(mock_config_loader)


@pytest.fixture
def text_generator(mock_config_loader, source_rank):
    """Returns a TextGenerator instance with mocked dependencies."""
    with (
        patch(
            "osa_tool.analytics.metadata.load_data_metadata",
            return_value=MagicMock(name="testrepo"),
        ),
        patch("osa_tool.models.models.ModelHandlerFactory.build") as mock_model,
    ):

        mock_model.return_value.send_request.return_value = json.dumps({})
        return TextGenerator(mock_config_loader, source_rank)


@pytest.fixture
def default_report():
    """Returns a RepositoryReport with default values."""
    return RepositoryReport()


@pytest.fixture
def custom_report():
    """Returns a RepositoryReport with custom-defined values."""
    return RepositoryReport(
        structure={
            "compliance": "Good",
            "missing_files": ["setup.py"],
            "organization": "Well structured",
        },
        readme={"readme_quality": "Good", "project_description": YesNoPartial.YES},
        documentation={
            "tests_present": YesNoPartial.YES,
            "docs_quality": "High",
            "outdated_content": True,
        },
        assessment={
            "key_shortcomings": ["No CI/CD"],
            "recommendations": ["Add GitHub Actions"],
        },
    )


@pytest.fixture
@patch("osa_tool.analytics.metadata.load_data_metadata")
@patch("osa_tool.models.models.ModelHandlerFactory.build")
def report_generator(mock_model, mock_load_data_metadata, mock_config_loader, source_rank):
    """Return a ReportGenerator instance with mocked dependencies."""
    mock_model.return_value.send_request.return_value = json.dumps({})

    return ReportGenerator(mock_config_loader, source_rank)
