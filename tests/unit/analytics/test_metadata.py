from unittest.mock import patch

import pytest
from requests.exceptions import HTTPError

from osa_tool.analytics.metadata import load_data_metadata, RepositoryMetadata, detect_platform


@pytest.mark.parametrize("mock_config_loader", ["github"], indirect=True)
def test_load_github_metadata_success(mock_config_loader, mock_requests_response_factory, mock_api_response_metadata):
    # Arrange
    mock_response = mock_requests_response_factory(status_code=200, json_data=mock_api_response_metadata)

    # Act
    with patch("osa_tool.analytics.metadata.requests.get", return_value=mock_response) as mock_get:
        metadata = load_data_metadata(mock_config_loader.config.git.repository)

    # Assert
    mock_get.assert_called_once()
    assert isinstance(metadata, RepositoryMetadata)
    assert metadata.full_name == mock_config_loader.config.git.full_name


@pytest.mark.parametrize("mock_config_loader", ["gitlab"], indirect=True)
def test_load_gitlab_metadata_success(mock_config_loader, mock_requests_response_factory, mock_api_response_metadata):
    # Arrange
    mock_response = mock_requests_response_factory(status_code=200, json_data=mock_api_response_metadata)

    # Act
    with patch("osa_tool.analytics.metadata.requests.get", return_value=mock_response) as mock_get:
        metadata = load_data_metadata(mock_config_loader.config.git.repository)

    # Assert
    mock_get.assert_called_once()
    assert isinstance(metadata, RepositoryMetadata)
    assert metadata.full_name == mock_config_loader.config.git.full_name


@pytest.mark.parametrize("mock_config_loader", ["gitverse"], indirect=True)
def test_load_gitverse_metadata_success(mock_config_loader, mock_requests_response_factory, mock_api_response_metadata):
    # Arrange
    mock_response = mock_requests_response_factory(status_code=200, json_data=mock_api_response_metadata)

    # Act
    with patch("osa_tool.analytics.metadata.requests.get", return_value=mock_response) as mock_get:
        metadata = load_data_metadata(mock_config_loader.config.git.repository)

    # Assert
    mock_get.assert_called_once()
    assert isinstance(metadata, RepositoryMetadata)
    assert metadata.full_name == mock_config_loader.config.git.full_name


@pytest.mark.parametrize("status_code", [401, 403, 404])
@pytest.mark.parametrize("mock_config_loader", ["github"], indirect=True)
def test_load_data_metadata_http_errors(mock_config_loader, mock_requests_response_factory, status_code):
    # Arrange
    mock_response = mock_requests_response_factory(status_code=status_code)

    # Assert
    with patch("osa_tool.analytics.metadata.requests.get", return_value=mock_response):
        with pytest.raises(HTTPError):
            load_data_metadata(mock_config_loader.config.git.repository)


@pytest.mark.parametrize("mock_config_loader", ["github"], indirect=True)
def test_load_data_metadata_unexpected_exception(mock_config_loader):
    # Assert
    with patch("osa_tool.analytics.metadata.requests.get", side_effect=Exception("Unexpected Error")):
        with pytest.raises(Exception):
            load_data_metadata(mock_config_loader.config.git.repository)


@pytest.mark.parametrize("mock_config_loader", ["github", "gitlab", "gitverse"], indirect=True)
def test_detect_platform_with_fixture(mock_config_loader):
    # Arrange
    repo_url = mock_config_loader.config.git.repository
    expected_platform = mock_config_loader.config.git.host

    # Assert
    assert detect_platform(repo_url) == expected_platform


@pytest.mark.parametrize("mock_config_loader", ["unsupported_platform"], indirect=True)
def test_detect_platform_unsupported_with_fixture(mock_config_loader):
    # Arrange
    repo_url = mock_config_loader.config.git.repository

    # Assert
    with pytest.raises(ValueError, match="Unsupported platform"):
        detect_platform(repo_url)
