from osa_tool.operations.docs.community_docs_generation.license_generation import LicenseCompiler
from osa_tool.scheduler.plan import Plan
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_license_already_exists(
    sourcerank_with_repo_tree,
    mock_repository_metadata,
    mock_config_manager,
    caplog,
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    plan = Plan({"ensure_license": "mit"})

    compiler = LicenseCompiler(
        config_manager=mock_config_manager,
        metadata=mock_repository_metadata,
        plan=plan,
    )
    compiler.sourcerank = sourcerank

    caplog.set_level("INFO")

    # Act
    compiler.run()

    # Assert
    assert "LICENSE file already exists." in caplog.text


def test_license_generated_successfully(
    tmp_path,
    sourcerank_with_repo_tree,
    mock_repository_metadata,
    mock_config_manager,
    caplog,
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    sourcerank.repo_path = tmp_path
    plan = Plan({"ensure_license": "mit"})

    compiler = LicenseCompiler(
        config_manager=mock_config_manager,
        metadata=mock_repository_metadata,
        plan=plan,
    )
    compiler.sourcerank = sourcerank

    caplog.set_level("INFO")

    # Act
    compiler.run()

    # Assert
    license_file = tmp_path / "LICENSE"
    assert license_file.exists()
    assert f"{mock_repository_metadata.created_at[:4]} " f"{mock_repository_metadata.owner}" in license_file.read_text()
    assert "LICENSE has been successfully compiled at" in caplog.text


def test_unknown_license_type(
    tmp_path,
    sourcerank_with_repo_tree,
    mock_repository_metadata,
    mock_config_manager,
    caplog,
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    sourcerank.repo_path = tmp_path
    plan = Plan({"ensure_license": "unknown_license"})

    compiler = LicenseCompiler(
        config_manager=mock_config_manager,
        metadata=mock_repository_metadata,
        plan=plan,
    )
    compiler.sourcerank = sourcerank

    caplog.set_level("ERROR")

    # Act
    compiler.run()

    # Assert
    assert f"Couldn't resolve {plan.get('ensure_license')} license type" in caplog.text
