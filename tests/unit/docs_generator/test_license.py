from osa_tool.operations.docs.community_docs_generation.license_generation import compile_license_file
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_license_already_exists(sourcerank_with_repo_tree, mock_repository_metadata, caplog):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    caplog.set_level("INFO")

    # Act
    compile_license_file(sourcerank, mock_repository_metadata, "mit")

    # Assert
    assert "LICENSE file already exists." in caplog.text


def test_license_generated_successfully(tmp_path, sourcerank_with_repo_tree, mock_repository_metadata, caplog):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    sourcerank.repo_path = tmp_path
    metadata = mock_repository_metadata
    caplog.set_level("INFO")

    # Act
    compile_license_file(sourcerank, mock_repository_metadata, "mit")

    # Assert
    license_file = tmp_path / "LICENSE"
    assert license_file.exists()
    assert f"{metadata.created_at[:4]} {metadata.owner}" in license_file.read_text()
    assert "LICENSE has been successfully compiled at" in caplog.text


def test_unknown_license_type(tmp_path, sourcerank_with_repo_tree, mock_repository_metadata, caplog):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    sourcerank.repo_path = tmp_path
    caplog.set_level("ERROR")
    unknown_license = "unknown_license"
    # Act
    compile_license_file(sourcerank, mock_repository_metadata, unknown_license)

    # Assert
    assert f"Couldn't resolve {unknown_license} license type, try to look up available licenses" in caplog.text
