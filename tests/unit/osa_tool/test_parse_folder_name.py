from osa_tool.utils import parse_folder_name


def test_parse_folder_name_with_trailing_slash(repo_url):
    # Act
    folder_name = parse_folder_name(repo_url + "/")
    # Assert
    assert folder_name == "username_repo-name"


def test_parse_folder_name_without_trailing_slash(repo_url):
    # Act
    folder_name = parse_folder_name(repo_url)
    # Assert
    assert folder_name == "username_repo-name"
