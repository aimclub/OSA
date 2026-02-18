from osa_tool.utils import parse_folder_name


def test_parse_folder_name_with_trailing_slash(repo_url):
    """
    Test that `parse_folder_name` correctly handles a repository URL with a trailing slash.
    
    Parameters
    ----------
    repo_url : str
        The base URL of the repository to be parsed.
    
    Returns
    -------
    None
    
    This test appends a trailing slash to the provided repository URL, calls
    `parse_folder_name`, and asserts that the returned folder name is
    "repo-name". It verifies that the parser correctly strips the trailing
    slash and extracts the repository name.
    """
    # Act
    folder_name = parse_folder_name(repo_url + "/")
    # Assert
    assert folder_name == "repo-name"


def test_parse_folder_name_without_trailing_slash(repo_url):
    """
    Test that `parse_folder_name` correctly extracts the folder name from a repository URL that does not end with a trailing slash.
    
    Parameters
    ----------
    repo_url
        The repository URL to be parsed.
    
    Returns
    -------
    None
    
    Raises
    ------
    AssertionError
        If the parsed folder name does not match the expected value "repo-name".
    """
    # Act
    folder_name = parse_folder_name(repo_url)
    # Assert
    assert folder_name == "repo-name"
