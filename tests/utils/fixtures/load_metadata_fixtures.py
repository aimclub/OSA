import pytest


@pytest.fixture
def mock_api_response_metadata(data_factory, repo_info):
    platform, owner, repo_name, repo_url = repo_info
    return data_factory.generate_repository_metadata_raw(platform, owner, repo_name, repo_url)
