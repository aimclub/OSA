import pytest


@pytest.fixture
def mock_api_response_metadata(data_factory, repo_info):
    """
    Generates simulated raw repository metadata by extracting repository details and using a data factory.
    
    This method unpacks repository information including the platform, owner, name, and URL, then utilizes the provided data factory to create a comprehensive metadata dictionary. This is used to produce realistic, fake data for testing or demonstration without querying actual APIs.
    
    Args:
        data_factory: An object used to generate simulated repository data. It must have a `generate_repository_metadata_raw` method.
        repo_info: A tuple or list containing, in order: the platform (e.g., 'github', 'gitlab'), the owner, the repository name, and the repository URL.
    
    Returns:
        dict: A dictionary containing detailed raw repository metadata. The structure and specific fields (e.g., star counts, dates, URLs) are determined by the data factory and vary based on the provided platform.
    """
    platform, owner, repo_name, repo_url = repo_info
    return data_factory.generate_repository_metadata_raw(platform, owner, repo_name, repo_url)
