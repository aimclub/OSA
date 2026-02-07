from unittest.mock import patch, mock_open, MagicMock

import pytest
import yaml

from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.scheduler.plan import Plan
from osa_tool.scheduler.workflow_manager import (
    GitHubWorkflowManager,
    GitLabWorkflowManager,
    GitverseWorkflowManager,
)


@pytest.fixture
def mock_args():
    """Mock CLI args with workflow-related flags."""
    args = MagicMock()
    for key in [
        "generate_workflows",
        "include_black",
        "include_tests",
        "include_pep8",
        "include_autopep8",
        "include_fix_pep8",
        "slash_command_dispatch",
        "pypi_publish",
        "python_versions",
    ]:
        setattr(args, key, True)
    return args


def test_has_python_code_true(mock_repository_metadata, mock_config_manager, mock_args):
    # Arrange
    manager = GitHubWorkflowManager(
        repo_url=mock_config_manager.config.git.repository,
        metadata=mock_repository_metadata,
        args=mock_args,
    )
    mock_repository_metadata.language = "Python"

    # Assert
    assert manager.has_python_code() is True


def test_has_python_code_false(mock_repository_metadata, mock_config_manager, mock_args):
    # Arrange
    manager = GitHubWorkflowManager(
        repo_url=mock_config_manager.config.git.repository,
        metadata=mock_repository_metadata,
        args=mock_args,
    )
    mock_repository_metadata.language = "JavaScript"

    # Assert
    assert manager.has_python_code() is False


def test_build_actual_plan_no_python(mock_repository_metadata, mock_config_manager, mock_args):
    # Arrange
    manager = GitHubWorkflowManager(
        repo_url=mock_config_manager.config.git.repository,
        metadata=mock_repository_metadata,
        args=mock_args,
    )
    mock_repository_metadata.language = None
    sourcerank = MagicMock(spec=SourceRank)

    # Act
    plan = manager.build_actual_plan(sourcerank)

    # Assert
    for key in plan:
        if key != "generate_workflows":
            assert plan[key] is False
    assert plan["generate_workflows"] is False


def test_build_actual_plan_with_existing_jobs(mock_repository_metadata, mock_config_manager, mock_args):
    # Arrange
    manager = GitHubWorkflowManager(
        repo_url=mock_config_manager.config.git.repository,
        metadata=mock_repository_metadata,
        args=mock_args,
    )
    mock_repository_metadata.language = "Python"
    manager.existing_jobs = {"test", "lint"}
    sourcerank = MagicMock(spec=SourceRank)
    sourcerank.tests_presence.return_value = True

    # Act
    plan = manager.build_actual_plan(sourcerank)

    # Assert
    assert plan["include_tests"] is False
    assert plan["include_pep8"] is False
    assert plan["include_black"] is False
    assert any(v is True for k, v in plan.items() if k != "generate_workflows")
    assert plan["generate_workflows"] is True


def test_update_workflow_config(mock_config_manager, mock_repository_metadata, mock_args):
    # Arrange
    manager = GitHubWorkflowManager(
        repo_url=mock_config_manager.config.git.repository,
        metadata=mock_repository_metadata,
        args=mock_args,
    )
    plan = Plan({"include_tests": True, "include_black": False, "python_versions": ["3.10"]})

    # Act
    manager.update_workflow_config(mock_config_manager, plan)
    updated = mock_config_manager.config.workflows

    # Assert
    assert updated.include_tests is True
    assert updated.include_black is False
    assert updated.python_versions == ["3.10"]


def test_github_locate_workflow_path_exists(mock_config_manager, mock_repository_metadata, mock_args):
    # Arrange
    with (
        patch("osa_tool.scheduler.workflow_manager.os.path.isdir", return_value=True),
        patch("osa_tool.scheduler.workflow_manager.os.listdir", return_value=[]),
        patch("osa_tool.scheduler.workflow_manager.open", mock_open()),
        patch("osa_tool.scheduler.workflow_manager.yaml.safe_load", return_value={}),
    ):
        manager = GitHubWorkflowManager(
            repo_url=mock_config_manager.config.git.repository,
            metadata=mock_repository_metadata,
            args=mock_args,
        )

        # Assert
        assert manager.workflow_path is not None
        assert ".github/workflows" in manager.workflow_path.replace("\\", "/")


def test_github_find_existing_jobs(mock_config_manager, mock_repository_metadata, mock_args):
    # Arrange
    yaml_content = {"jobs": {"test": {}, "lint": {}}}
    with (
        patch("osa_tool.scheduler.workflow_manager.os.path.isdir", return_value=True),
        patch("osa_tool.scheduler.workflow_manager.os.listdir", return_value=["ci.yml"]),
        patch("osa_tool.scheduler.workflow_manager.open", mock_open(read_data=yaml.dump(yaml_content))),
        patch("osa_tool.scheduler.workflow_manager.yaml.safe_load", return_value=yaml_content),
    ):
        manager = GitHubWorkflowManager(
            repo_url=mock_config_manager.config.git.repository,
            metadata=mock_repository_metadata,
            args=mock_args,
        )

        # Act
        jobs = manager._find_existing_jobs()

        # Assert
        assert jobs == {"test", "lint"}


@pytest.mark.parametrize("mock_config_manager", ["gitlab"], indirect=True)
def test_gitlab_locate_workflow_path_exists(mock_config_manager, mock_repository_metadata, mock_args):
    # Arrange
    with (
        patch("osa_tool.scheduler.workflow_manager.os.path.isfile", return_value=True),
        patch("osa_tool.scheduler.workflow_manager.open", mock_open()),
        patch("osa_tool.scheduler.workflow_manager.yaml.safe_load", return_value={}),
    ):
        manager = GitLabWorkflowManager(
            repo_url=mock_config_manager.config.git.repository,
            metadata=mock_repository_metadata,
            args=mock_args,
        )

        # Assert
        assert manager.workflow_path is not None
        assert manager.workflow_path.endswith(".gitlab-ci.yml")


@pytest.mark.parametrize("mock_config_manager", ["gitlab"], indirect=True)
def test_gitlab_find_existing_jobs(mock_config_manager, mock_repository_metadata, mock_args):
    # Arrange
    yaml_content = {
        "stages": ["test"],
        "variables": {"PY": "python3"},
        "test_job": {"script": ["pytest"]},
        "build": {"script": ["make"]},
    }
    with (
        patch("osa_tool.scheduler.workflow_manager.os.path.isfile", return_value=True),
        patch("osa_tool.scheduler.workflow_manager.open", mock_open(read_data=yaml.dump(yaml_content))),
        patch("osa_tool.scheduler.workflow_manager.yaml.safe_load", return_value=yaml_content),
    ):
        manager = GitLabWorkflowManager(
            repo_url=mock_config_manager.config.git.repository,
            metadata=mock_repository_metadata,
            args=mock_args,
        )

        # Act
        jobs = manager._find_existing_jobs()

        # Assert
        assert jobs == {"test_job", "build"}


@pytest.mark.parametrize("mock_config_manager", ["gitverse"], indirect=True)
def test_gitverse_locate_workflow_path_gitverse_exists(mock_config_manager, mock_repository_metadata, mock_args):
    # Arrange
    def isdir_side_effect(path):
        return ".gitverse/workflows" in path.replace("\\", "/")

    with (
        patch("osa_tool.scheduler.workflow_manager.os.path.isdir", side_effect=isdir_side_effect),
        patch("osa_tool.scheduler.workflow_manager.os.listdir", return_value=[]),
        patch("osa_tool.scheduler.workflow_manager.open", mock_open()),
        patch("osa_tool.scheduler.workflow_manager.yaml.safe_load", return_value={}),
    ):
        manager = GitverseWorkflowManager(
            repo_url=mock_config_manager.config.git.repository,
            metadata=mock_repository_metadata,
            args=mock_args,
        )

        # Assert
        assert manager.workflow_path is not None
        assert ".gitverse/workflows" in manager.workflow_path.replace("\\", "/")


@pytest.mark.parametrize("mock_config_manager", ["gitverse"], indirect=True)
def test_gitverse_locate_workflow_path_fallback_to_github(mock_config_manager, mock_repository_metadata, mock_args):
    # Arrange
    def isdir_side_effect(path):
        return ".github/workflows" in path.replace("\\", "/")

    with (
        patch("osa_tool.scheduler.workflow_manager.os.path.isdir", side_effect=isdir_side_effect),
        patch("osa_tool.scheduler.workflow_manager.os.listdir", return_value=[]),
        patch("osa_tool.scheduler.workflow_manager.open", mock_open()),
        patch("osa_tool.scheduler.workflow_manager.yaml.safe_load", return_value={}),
    ):
        manager = GitverseWorkflowManager(
            repo_url=mock_config_manager.config.git.repository,
            metadata=mock_repository_metadata,
            args=mock_args,
        )

        # Assert
        assert manager.workflow_path is not None
        assert ".github/workflows" in manager.workflow_path.replace("\\", "/")
