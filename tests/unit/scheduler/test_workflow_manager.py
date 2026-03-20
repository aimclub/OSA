from unittest.mock import patch, mock_open, MagicMock

import pytest
import yaml

from osa_tool.scheduler.plan import Plan
from osa_tool.scheduler.workflow_manager import (
    GitHubWorkflowManager,
    GitLabWorkflowManager,
    GitverseWorkflowManager,
)
from osa_tool.tools.repository_analysis.sourcerank import SourceRank


@pytest.fixture
def mock_args():
    """
    Mock CLI args with workflow-related flags.
    
    Creates a MagicMock object that simulates parsed command-line arguments for testing
    workflow-related operations. Each flag is set to True to represent a typical
    configuration where all workflow features are enabled.
    
    Args:
        None
    
    Returns:
        A MagicMock object with boolean attributes corresponding to workflow flags.
        The attributes include:
            - generate_workflows
            - include_black
            - include_tests
            - include_pep8
            - include_autopep8
            - include_fix_pep8
            - slash_command_dispatch
            - pypi_publish
            - python_versions
    """
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
    """
    Verifies that has_python_code returns True when the repository metadata identifies the primary language as Python.
    
    This test ensures the method correctly identifies Python repositories based on the primary language field in metadata, without needing to scan for .py files.
    
    Args:
        mock_repository_metadata: A mock object representing the repository's metadata.
        mock_config_manager: A mock object providing access to configuration settings.
        mock_args: A mock object containing command-line arguments or execution flags.
    
    Returns:
        None.
    """
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
    """
    Verifies that the has_python_code method returns False when the repository language is not Python.
    
    This test ensures the method correctly identifies non-Python repositories by setting the metadata language to a non-Python value (e.g., "JavaScript") and asserting that has_python_code returns False.
    
    Args:
        mock_repository_metadata: A mock object containing repository metadata, including the primary programming language.
        mock_config_manager: A mock configuration manager providing access to git and repository settings.
        mock_args: A mock object representing command-line arguments or execution parameters.
    
    Returns:
        None.
    """
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
    """
    Verifies that the workflow generation plan is correctly disabled when no Python language is detected in the repository.
    
    This test ensures that the `build_actual_plan` method returns a plan where all generation flags, specifically `generate_workflows`, are set to `False` when the repository metadata indicates the absence of Python. This is because the OSA Tool's workflow generation is primarily intended for Python projects, so it should be disabled for non-Python repositories to avoid unnecessary or irrelevant automation.
    
    Args:
        mock_repository_metadata: Mocked metadata object containing repository information like language. In this test, its language attribute is set to None to simulate a non-Python repository.
        mock_config_manager: Mocked configuration manager providing access to git and repository settings.
        mock_args: Mocked command-line arguments passed to the manager.
    
    Steps performed:
    1. Arrange: Creates a GitHubWorkflowManager instance with the provided mocks and sets the repository language to None.
    2. Act: Calls `build_actual_plan` with a mocked SourceRank object.
    3. Assert: Verifies that every key in the returned plan dictionary is False, including the `generate_workflows` flag.
    """
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
    """
    Verifies that the workflow generation plan correctly excludes jobs that already exist in the repository.
    Specifically, tests that when certain jobs (like 'test' and 'lint') are already present, they are omitted from the generated plan.
    This ensures the tool does not duplicate existing workflows.
    
    Args:
        mock_repository_metadata: Mocked metadata containing repository information such as language.
        mock_config_manager: Mocked configuration manager providing access to git repository settings.
        mock_args: Mocked command-line arguments used for initializing the manager.
    
    Returns:
        None.
    """
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
    """
    Verifies that the update_workflow_config method correctly updates the workflow configuration settings within the configuration manager based on a provided plan.
    
    This test ensures that the GitHubWorkflowManager properly applies a workflow plan to the configuration manager, updating settings such as test inclusion, code formatting tools, and Python version specifications.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to simulate repository and workflow settings.
        mock_repository_metadata: A mocked metadata object containing repository-specific information.
        mock_args: A mocked arguments object representing command-line or runtime inputs.
    
    Why:
        The test validates the integration between the workflow manager and the configuration system, confirming that planned workflow changes are accurately reflected in the configuration state. This is critical for ensuring that automated repository enhancements are applied as intended.
    """
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
    """
    Verifies that the GitHubWorkflowManager correctly identifies and sets the workflow path when the directory exists.
    
    This test ensures that when the `.github/workflows` directory is present in the repository, the manager successfully locates it and assigns the correct path to the `workflow_path` attribute. The test uses mocked filesystem operations to simulate an existing directory with no workflow files, confirming the manager's ability to handle this scenario without relying on actual file system state.
    
    Args:
        mock_config_manager: A mocked configuration manager providing repository settings.
        mock_repository_metadata: Mocked metadata associated with the repository.
        mock_args: Mocked command-line arguments or parameters.
    """
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
    """
    Verifies that the GitHubWorkflowManager correctly identifies and extracts existing job names from local workflow files.
    
    This test ensures the manager can parse a repository's workflow YAML files to retrieve the set of defined job names, which is necessary for avoiding duplicate job creation and understanding the existing CI/CD structure.
    
    Args:
        mock_config_manager: Mocked configuration manager providing repository settings.
        mock_repository_metadata: Mocked metadata for the repository being processed.
        mock_args: Mocked command-line arguments.
    
    Returns:
        None.
    """
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
    """
    Verifies that the GitLabWorkflowManager correctly locates the workflow path when the configuration file exists.
    
    This test ensures the manager can find the standard GitLab CI/CD configuration file (`.gitlab-ci.yml`) when it is present in the repository. It uses patched file operations to simulate the existence of the file without actual filesystem interaction.
    
    Args:
        mock_config_manager: A mocked configuration manager providing GitLab repository settings.
        mock_repository_metadata: Mocked metadata associated with the repository.
        mock_args: Mocked command-line arguments or configuration parameters.
    
    Note:
        The test is parameterized to run with a GitLab-specific mock configuration manager.
        It patches `os.path.isfile` to return `True`, `open` with a mock, and `yaml.safe_load` to return an empty dictionary, simulating a valid but empty configuration file.
        The assertions confirm that the manager's `workflow_path` is not `None` and ends with the expected filename `.gitlab-ci.yml`.
    """
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
    """
    Verifies that the GitLabWorkflowManager correctly identifies and extracts job names from a GitLab CI YAML configuration file.
    This test ensures the manager can parse a YAML structure and return only the keys that represent job definitions, excluding other top-level keys like 'stages' and 'variables'.
    
    Args:
        mock_config_manager: A mocked configuration manager providing GitLab-specific settings.
        mock_repository_metadata: Mocked metadata containing repository information.
        mock_args: Mocked command-line arguments used for manager initialization.
    """
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
    """
    Verifies that the GitverseWorkflowManager correctly locates the workflow path when a .gitverse directory exists.
    
    This test ensures the manager identifies the correct workflow directory path when a `.gitverse/workflows` folder is present in the repository. It mocks filesystem operations to simulate the existence of this directory and validates that the manager's `workflow_path` property is set accordingly.
    
    Args:
        mock_config_manager: Mocked configuration manager providing repository settings.
        mock_repository_metadata: Mocked metadata for the repository being processed.
        mock_args: Mocked command-line arguments.
    
    Note:
        The test uses `pytest.mark.parametrize` to run with a specific mock configuration ("gitverse").
        Filesystem calls (`os.path.isdir`, `os.listdir`, `open`, `yaml.safe_load`) are patched to control the test environment and avoid actual filesystem dependencies.
    """
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
    """
    Verifies that the GitverseWorkflowManager correctly falls back to the '.github/workflows' directory when the Gitverse-specific workflow path is not found.
    
    This test simulates a scenario where the expected Gitverse workflow directory does not exist. The manager's `workflow_path` property should then default to the standard '.github/workflows' location.
    
    Args:
        mock_config_manager: Mocked configuration manager providing repository settings.
        mock_repository_metadata: Mocked metadata for the repository being processed.
        mock_args: Mocked command-line arguments.
    
    The test uses mocking to make the '.github/workflows' directory appear as the only valid path, ensuring the fallback behavior is triggered and validated.
    """
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
