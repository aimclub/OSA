from osa_tool.docs_generator.license import compile_license_file
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_license_already_exists(sourcerank_with_repo_tree, load_metadata_license, caplog):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    caplog.set_level("INFO")

    # Act
    compile_license_file(sourcerank, ensure_license="mit")

    # Assert
    assert "LICENSE file already exists." in caplog.text
    load_metadata_license.assert_not_called()


def test_license_generated_successfully(tmp_path, sourcerank_with_repo_tree, load_metadata_license, caplog):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    sourcerank.repo_path = tmp_path
    metadata = load_metadata_license.return_value
    caplog.set_level("INFO")

    # Act
    compile_license_file(sourcerank, ensure_license="mit")

    # Assert
    license_file = tmp_path / "LICENSE"
    assert license_file.exists()
    assert f"{metadata.created_at[:4]} {metadata.owner}" in license_file.read_text()
    assert "LICENSE has been successfully compiled at" in caplog.text


def test_unknown_license_type(tmp_path, sourcerank_with_repo_tree, load_metadata_license, caplog):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    sourcerank.repo_path = tmp_path
    caplog.set_level("ERROR")
    unknown_license = "unknown_license"
    # Act
    compile_license_file(sourcerank, ensure_license=unknown_license)

    # Assert
    assert f"Couldn't resolve {unknown_license} license type, try to look up available licenses" in caplog.text
