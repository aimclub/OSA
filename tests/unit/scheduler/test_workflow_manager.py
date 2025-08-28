from unittest import mock
from unittest.mock import patch

import pytest
import yaml

from osa_tool.scheduler.workflow_manager import WorkflowManager, generate_github_workflows, update_workflow_config
from tests.utils.mocks.repo_trees import get_mock_repo_tree


@pytest.fixture
def sample_workflows_plan():
    return {
        "include_black": True,
        "include_tests": True,
        "include_pep8": True,
        "include_autopep8": False,
        "include_fix_pep8": False,
        "slash-command-dispatch": False,
        "pypi-publish": False,
        "generate_workflows": True,
    }


def test_workflow_manager_initialization(
    mock_config_loader, mock_repository_metadata, sourcerank_with_repo_tree, sample_workflows_plan, tmp_path
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    base_path = str(tmp_path)

    # Act
    manager = WorkflowManager(base_path, sourcerank, mock_repository_metadata, sample_workflows_plan)

    # Assert
    assert manager.base_path == base_path
    assert manager.sourcerank == sourcerank
    assert manager.metadata == mock_repository_metadata
    assert manager.workflows_plan == sample_workflows_plan
    assert isinstance(manager.excluded_keys, set)
    assert isinstance(manager.job_name_for_key, dict)


def test_find_workflows_directory_exists(
    mock_config_loader, mock_repository_metadata, mock_sourcerank, sample_workflows_plan, tmp_path
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = mock_sourcerank(repo_tree_data)
    base_path = str(tmp_path)
    manager = WorkflowManager(base_path, sourcerank, mock_repository_metadata, sample_workflows_plan)

    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)

    # Act
    result = manager._find_workflows_directory()

    # Assert
    assert result == str(workflows_dir)


def test_find_workflows_directory_not_exists(
    mock_config_loader, mock_repository_metadata, mock_sourcerank, sample_workflows_plan, tmp_path
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = mock_sourcerank(repo_tree_data)
    base_path = str(tmp_path)
    manager = WorkflowManager(base_path, sourcerank, mock_repository_metadata, sample_workflows_plan)

    # Act
    result = manager._find_workflows_directory()

    # Assert
    assert result is None


def test_has_python_code_with_python(
    mock_config_loader, mock_repository_metadata, mock_sourcerank, sample_workflows_plan, tmp_path
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = mock_sourcerank(repo_tree_data)
    base_path = str(tmp_path)
    manager = WorkflowManager(base_path, sourcerank, mock_repository_metadata, sample_workflows_plan)
    mock_repository_metadata.language = {"Python": 100}

    # Act
    result = manager._has_python_code()

    # Assert
    assert result is True


def test_has_python_code_without_python(
    mock_config_loader, mock_repository_metadata, mock_sourcerank, sample_workflows_plan, tmp_path
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = mock_sourcerank(repo_tree_data)
    base_path = str(tmp_path)
    manager = WorkflowManager(base_path, sourcerank, mock_repository_metadata, sample_workflows_plan)
    mock_repository_metadata.language = {"JavaScript": 100}

    # Act
    result = manager._has_python_code()

    # Assert
    assert result is False


def test_has_python_code_no_language(
    mock_config_loader, mock_repository_metadata, mock_sourcerank, sample_workflows_plan, tmp_path
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = mock_sourcerank(repo_tree_data)
    base_path = str(tmp_path)
    manager = WorkflowManager(base_path, sourcerank, mock_repository_metadata, sample_workflows_plan)
    mock_repository_metadata.language = None

    # Act
    result = manager._has_python_code()

    # Assert
    assert result is False


def test_get_existing_jobs_no_workflows_dir(
    mock_config_loader, mock_repository_metadata, mock_sourcerank, sample_workflows_plan, tmp_path
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = mock_sourcerank(repo_tree_data)
    base_path = str(tmp_path)
    manager = WorkflowManager(base_path, sourcerank, mock_repository_metadata, sample_workflows_plan)
    manager.workflows_dir = None

    # Act
    existing_jobs = manager._get_existing_jobs()

    # Assert
    assert isinstance(existing_jobs, set)
    assert len(existing_jobs) == 0


def test_get_existing_jobs_empty_directory(
    mock_config_loader, mock_repository_metadata, mock_sourcerank, sample_workflows_plan, tmp_path
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = mock_sourcerank(repo_tree_data)
    base_path = str(tmp_path)
    manager = WorkflowManager(base_path, sourcerank, mock_repository_metadata, sample_workflows_plan)

    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    manager.workflows_dir = str(workflows_dir)

    # Act
    existing_jobs = manager._get_existing_jobs()

    # Assert
    assert isinstance(existing_jobs, set)
    assert len(existing_jobs) == 0


def test_get_existing_jobs_with_valid_yaml(
    mock_config_loader, mock_repository_metadata, mock_sourcerank, sample_workflows_plan, tmp_path
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = mock_sourcerank(repo_tree_data)
    base_path = str(tmp_path)
    manager = WorkflowManager(base_path, sourcerank, mock_repository_metadata, sample_workflows_plan)

    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    manager.workflows_dir = str(workflows_dir)

    workflow_file = workflows_dir / "test.yml"
    workflow_content = {"jobs": {"test": {"runs-on": "ubuntu-latest"}, "build": {"runs-on": "ubuntu-latest"}}}
    with open(workflow_file, "w") as f:
        yaml.dump(workflow_content, f)

    # Act
    existing_jobs = manager._get_existing_jobs()

    # Assert
    assert isinstance(existing_jobs, set)
    assert "test" in existing_jobs
    assert "build" in existing_jobs
    assert len(existing_jobs) == 2


def test_get_existing_jobs_with_invalid_yaml(
    mock_config_loader, mock_repository_metadata, mock_sourcerank, sample_workflows_plan, tmp_path
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = mock_sourcerank(repo_tree_data)
    base_path = str(tmp_path)
    manager = WorkflowManager(base_path, sourcerank, mock_repository_metadata, sample_workflows_plan)

    workflows_dir = tmp_path / ".github" / "workflows"
    workflows_dir.mkdir(parents=True)
    manager.workflows_dir = str(workflows_dir)

    invalid_file = workflows_dir / "invalid.yml"
    with open(invalid_file, "w") as f:
        f.write("invalid: yaml: content:")

    # Act
    existing_jobs = manager._get_existing_jobs()

    # Assert
    assert isinstance(existing_jobs, set)
    assert len(existing_jobs) == 0


def test_build_actual_plan_no_python_code(
    mock_config_loader, mock_repository_metadata, mock_sourcerank, sample_workflows_plan, tmp_path
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = mock_sourcerank(repo_tree_data)
    base_path = str(tmp_path)
    mock_repository_metadata.language = {"JavaScript": 100}

    manager = WorkflowManager(base_path, sourcerank, mock_repository_metadata, sample_workflows_plan)

    # Act
    actual_plan = manager.build_actual_plan()

    # Assert
    for key, value in actual_plan.items():
        if key != "generate_workflows":
            assert value is False
        else:
            assert value is False


def test_build_actual_plan_with_existing_jobs(
    mock_config_loader, mock_repository_metadata, mock_sourcerank, sample_workflows_plan, tmp_path
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = mock_sourcerank(repo_tree_data)
    base_path = str(tmp_path)
    mock_repository_metadata.language = {"Python": 100}

    manager = WorkflowManager(base_path, sourcerank, mock_repository_metadata, sample_workflows_plan)
    manager.existing_jobs = {"black"}

    # Act
    actual_plan = manager.build_actual_plan()

    # Assert
    assert actual_plan["include_black"] is False


def test_build_actual_plan_tests_without_tests_dir(
    mock_config_loader, mock_repository_metadata, mock_sourcerank, sample_workflows_plan, tmp_path
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = mock_sourcerank(repo_tree_data, method_overrides={"tests_presence": False})
    base_path = str(tmp_path)
    mock_repository_metadata.language = {"Python": 100}

    manager = WorkflowManager(base_path, sourcerank, mock_repository_metadata, sample_workflows_plan)

    # Act
    actual_plan = manager.build_actual_plan()

    # Assert
    assert actual_plan["include_tests"] is False


def test_update_workflow_config(mock_config_loader):
    # Arrange
    plan = {"include_black": True, "include_tests": False, "include_pep8": True}
    workflow_keys = ["include_black", "include_tests", "include_pep8"]

    with patch("osa_tool.scheduler.workflow_manager.logger") as mock_logger:

        # Act
        update_workflow_config(mock_config_loader, plan, workflow_keys)

        # Assert
        mock_logger.info.assert_called_once_with("Config successfully updated with workflow_settings")


def test_generate_github_workflows_success(mock_config_loader):
    with patch(
        "osa_tool.scheduler.workflow_manager.generate_workflows_from_settings", return_value=["file1.yml"]
    ) as mock_generate:
        # Act
        generate_github_workflows(mock_config_loader)

        # Assert
        mock_generate.assert_called_once()
        mock_generate.assert_called_with(mock_config_loader.config.workflows, mock.ANY)


def test_generate_github_workflows_no_files_created(mock_config_loader):
    with patch(
        "osa_tool.scheduler.workflow_manager.generate_workflows_from_settings", return_value=[]
    ) as mock_generate:
        # Act
        generate_github_workflows(mock_config_loader)

        # Assert
        mock_generate.assert_called_once()


def test_generate_github_workflows_exception_handling(mock_config_loader):
    with patch(
        "osa_tool.scheduler.workflow_manager.generate_workflows_from_settings", side_effect=Exception("Test error")
    ) as mock_generate:
        # Act
        generate_github_workflows(mock_config_loader)

        # Assert
        mock_generate.assert_called_once()
