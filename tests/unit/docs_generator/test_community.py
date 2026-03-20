import os
from unittest.mock import patch

import pytest

from osa_tool.operations.docs.community_docs_generation.community import CommunityTemplateBuilder
from tests.utils.mocks.repo_trees import get_mock_repo_tree


@pytest.fixture(autouse=True)
def mock_os_makedirs():
    """
    Mocks the `os.makedirs` function for the community docs generation module.
    
    This pytest fixture automatically patches the `os.makedirs` call within the
    `community_docs_generation` module to prevent actual directory creation during
    tests. It uses `unittest.mock.patch` to replace the real function with a mock
    for the duration of the test, ensuring tests do not create filesystem artifacts.
    
    Args:
        None.
    
    Yields:
        None: This is a context-managed fixture that yields control to the test.
        The patched mock is active inside the `with` block and is automatically
        cleaned up when the fixture exits.
    """
    with patch("osa_tool.operations.docs.community_docs_generation.community.os.makedirs"):
        yield


def test_community_template_builder_init(
    mock_config_manager,
    mock_repository_metadata,
):
    """
    Verifies the initialization of the CommunityTemplateBuilder class.
    
    This test ensures that when a CommunityTemplateBuilder instance is created, all expected attributes are correctly set based on the provided configuration and metadata. It validates that the internal template dictionary contains the required community template keys and that the generated file paths are correctly formatted for the specific git host (e.g., GitHub or GitLab).
    
    Args:
        mock_config_manager: A mocked configuration manager containing git and repository settings.
        mock_repository_metadata: A mocked metadata object containing repository information.
    
    Initializes the following class fields:
        repo_url: The URL of the git repository.
        metadata: The metadata associated with the repository.
        sourcerank: An object or value representing the source rank metrics.
        _template: A dictionary containing various community templates like code of conduct and issue types.
        repo_path: The local path where the repository is stored, suffixed by the git host.
        code_of_conduct_to_save: The file path for saving the code of conduct template.
        pr_to_save: The file path for saving the pull request or merge request template. The filename varies depending on the git host (PULL_REQUEST_TEMPLATE.md for GitHub, MERGE_REQUEST_TEMPLATE.md for GitLab).
        docs_issue_to_save: The file path for saving the documentation issue template.
        feature_issue_to_save: The file path for saving the feature issue template.
        bug_issue_to_save: The file path for saving the bug issue template.
    """
    # Act
    builder = CommunityTemplateBuilder(mock_config_manager, mock_repository_metadata)

    # Assert
    assert builder.repo_url == mock_config_manager.config.git.repository
    assert builder.metadata == mock_repository_metadata
    assert builder.sourcerank is not None
    assert "code_of_conduct" in builder._template
    assert "pull_request" in builder._template
    assert "docs_issue" in builder._template
    assert "feature_issue" in builder._template
    assert "bug_issue" in builder._template

    assert builder.repo_path.endswith(f".{mock_config_manager.config.git.host}")
    assert builder.code_of_conduct_to_save.endswith("CODE_OF_CONDUCT.md")
    if "github" in mock_config_manager.config.git.host:
        assert builder.pr_to_save.endswith("PULL_REQUEST_TEMPLATE.md")
    elif "gitlab" in mock_config_manager.config.git.host:
        assert builder.pr_to_save.endswith("MERGE_REQUEST_TEMPLATE.md")
    assert builder.docs_issue_to_save.endswith("DOCUMENTATION_ISSUE.md")
    assert builder.feature_issue_to_save.endswith("FEATURE_ISSUE.md")
    assert builder.bug_issue_to_save.endswith("BUG_ISSUE.md")


def test_build_code_of_conduct(mock_config_manager, mock_repository_metadata, tmp_path, caplog):
    """
    Verifies that the build_code_of_conduct method correctly triggers the generation and saving of the CODE_OF_CONDUCT.md file.
    
    This test ensures the method calls the underlying save operation and logs the expected success message.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used for setup.
        mock_repository_metadata: A mocked repository metadata instance used for setup.
        tmp_path: A pytest fixture providing a temporary directory path for file operations.
        caplog: A pytest fixture used to capture and inspect log messages.
    
    Returns:
        None.
    """
    # Arrange
    builder = CommunityTemplateBuilder(mock_config_manager, mock_repository_metadata)
    builder.repo_path = tmp_path / f".{mock_config_manager.config.git.host}"
    builder.code_of_conduct_to_save = builder.repo_path / "CODE_OF_CONDUCT.md"
    caplog.set_level("INFO")

    with patch("osa_tool.operations.docs.community_docs_generation.community.save_sections") as mock_save_sections:
        mock_save_sections.return_value = None

        # Act
        builder.build_code_of_conduct()

        # Assert
        mock_save_sections.assert_called_once()
        assert f"CODE_OF_CONDUCT.md successfully generated in folder {builder.repo_path}" in caplog.text


def test_build_pull_request(mock_config_manager, mock_repository_metadata, sourcerank_with_repo_tree, tmp_path, caplog):
    """
    Tests the build_pull_request method of CommunityTemplateBuilder.
    
    This test verifies that the CommunityTemplateBuilder.build_pull_request method correctly generates and saves a pull request template file. It sets up a mock environment with a SourceRank instance, repository path, and appropriate template filename based on the git host. The test patches the save_sections function to prevent actual file operations and checks that it was called correctly and that an appropriate success message was logged.
    
    The test adapts the template filename to the git host (e.g., PULL_REQUEST_TEMPLATE.md for GitHub, MERGE_REQUEST_TEMPLATE.md for others) to ensure compatibility with different platforms. This is why the filename is conditionally set before calling the method.
    
    Args:
        mock_config_manager: Mock configuration manager providing git host information.
        mock_repository_metadata: Mock repository metadata for the builder.
        sourcerank_with_repo_tree: Factory fixture to create SourceRank instance with repository tree data.
        tmp_path: Temporary directory path for testing file operations.
        caplog: Pytest fixture for capturing log messages.
    
    Returns:
        None
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = CommunityTemplateBuilder(mock_config_manager, mock_repository_metadata)
    builder.sourcerank = sourcerank
    builder.repo_path = tmp_path / f".{mock_config_manager.config.git.host}"
    if "github" in mock_config_manager.config.git.host:
        builder.pr_to_save = builder.repo_path / "PULL_REQUEST_TEMPLATE.md"
    else:
        builder.pr_to_save = builder.repo_path / "MERGE_REQUEST_TEMPLATE.md"
    caplog.set_level("INFO")

    with patch("osa_tool.operations.docs.community_docs_generation.community.save_sections") as mock_save_sections:
        mock_save_sections.return_value = None

        # Act
        builder.build_pull_request()

        # Assert
        mock_save_sections.assert_called_once()
        assert (
            f"PULL_REQUEST_TEMPLATE.md successfully generated in folder {os.path.dirname(builder.pr_to_save)}"
            in caplog.text
        )


def test_build_documentation_issue_with_docs_present(
    mock_config_manager, mock_repository_metadata, sourcerank_with_repo_tree, tmp_path, caplog
):
    """
    Tests the generation of the DOCUMENTATION_ISSUE.md file when documentation is present.
    
    This test arranges a CommunityTemplateBuilder instance with a mock repository
    tree containing documentation, then calls the `build_documentation_issue` method
    and verifies the file is generated successfully and logged.
    
    The test ensures that when documentation exists in the repository,
    the builder correctly triggers the issue generation process and logs the outcome.
    
    Args:
        mock_config_manager: A mocked configuration manager.
        mock_repository_metadata: Mocked repository metadata.
        sourcerank_with_repo_tree: A fixture factory to create a SourceRank instance
            with a given repository tree.
        tmp_path: A pytest fixture providing a temporary directory path.
        caplog: A pytest fixture for capturing log messages.
    
    Returns:
        None
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = CommunityTemplateBuilder(mock_config_manager, mock_repository_metadata)
    builder.sourcerank = sourcerank
    builder.repo_path = tmp_path / f".{mock_config_manager.config.git.host}"
    builder.docs_issue_to_save = builder.repo_path / "DOCUMENTATION_ISSUE.md"
    caplog.set_level("INFO")

    with patch("osa_tool.operations.docs.community_docs_generation.community.save_sections") as mock_save_sections:
        mock_save_sections.return_value = None

        # Act
        builder.build_documentation_issue()

        # Assert
        mock_save_sections.assert_called_once()
        assert "DOCUMENTATION_ISSUE.md successfully generated in folder" in caplog.text


def test_build_documentation_issue_without_docs_present(
    mock_config_manager, mock_repository_metadata, sourcerank_with_repo_tree, tmp_path
):
    """
    Tests the build_documentation_issue method when no documentation is present.
    
    This test verifies that the `CommunityTemplateBuilder.build_documentation_issue`
    method does not call the `save_sections` function when the repository lacks
    documentation files. This ensures the method correctly skips documentation generation
    when none is available, preventing unnecessary file operations.
    
    Args:
        mock_config_manager: A mocked configuration manager.
        mock_repository_metadata: Mocked repository metadata.
        sourcerank_with_repo_tree: A fixture factory to create a SourceRank instance
            with a given repository tree. The fixture is used to inject a minimal mock
            repository tree that contains no documentation files.
        tmp_path: A temporary directory path fixture, used to set the repository path
            for the builder.
    
    Returns:
        None
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = CommunityTemplateBuilder(mock_config_manager, mock_repository_metadata)
    builder.sourcerank = sourcerank
    builder.repo_path = tmp_path / f".{mock_config_manager.config.git.host}"
    builder.docs_issue_to_save = builder.repo_path / "DOCUMENTATION_ISSUE.md"

    with patch("osa_tool.operations.docs.community_docs_generation.community.save_sections") as mock_save_sections:
        # Act
        builder.build_documentation_issue()

        # Assert
        mock_save_sections.assert_not_called()


def test_build_feature_issue(mock_config_manager, mock_repository_metadata, tmp_path, caplog):
    """
    Verifies that the build_feature_issue method correctly triggers the generation and saving of the FEATURE_ISSUE.md file.
    
    This test ensures the CommunityTemplateBuilder's build_feature_issue method calls the appropriate internal save function and logs a success message. It uses mocked dependencies to isolate the behavior and avoid actual file system writes.
    
    Args:
        mock_config_manager: Mocked configuration manager providing git host settings.
        mock_repository_metadata: Mocked metadata for the repository being processed.
        tmp_path: Pytest fixture providing a temporary directory path for file operations.
        caplog: Pytest fixture to capture and inspect log messages.
    
    Attributes Initialized:
        repo_path: The local filesystem path where the repository templates are stored.
        feature_issue_to_save: The specific file path for the generated FEATURE_ISSUE.md.
    
    Why:
        The test validates that the feature issue documentation is properly generated and saved without performing real I/O, ensuring the method integrates correctly with the logging and file-saving subsystems.
    """
    # Arrange
    builder = CommunityTemplateBuilder(mock_config_manager, mock_repository_metadata)
    builder.repo_path = tmp_path / f".{mock_config_manager.config.git.host}"
    builder.feature_issue_to_save = builder.repo_path / "FEATURE_ISSUE.md"
    caplog.set_level("INFO")

    with patch("osa_tool.operations.docs.community_docs_generation.community.save_sections") as mock_save_sections:
        mock_save_sections.return_value = None

        # Act
        builder.build_feature_issue()

        # Assert
        mock_save_sections.assert_called_once()
        assert "FEATURE_ISSUE.md successfully generated in folder" in caplog.text


def test_build_bug_issue(mock_config_manager, mock_repository_metadata, tmp_path, caplog):
    """
    Tests the generation and saving of the bug issue template file.
    
    This test verifies that the `build_bug_issue` method correctly creates and saves a BUG_ISSUE.md file to the expected location within the repository structure. It also confirms that an appropriate log message is produced upon successful generation.
    
    Args:
        mock_config_manager: Mocked configuration manager instance.
        mock_repository_metadata: Mocked repository metadata instance.
        tmp_path: Pytest fixture providing a temporary directory path.
        caplog: Pytest fixture to capture log messages.
    
    The test performs the following steps:
    1. Arranges the test by creating a `CommunityTemplateBuilder` instance and setting its `repo_path` and `bug_issue_to_save` attributes based on the mocked configuration and temporary path.
    2. Mocks the `save_sections` function to isolate the file system operation.
    3. Acts by calling the `build_bug_issue` method.
    4. Asserts that `save_sections` was called exactly once and that a success message appears in the captured logs.
    
    Why this structure is used: The test isolates the file-saving behavior by mocking the external `save_sections` call, allowing verification of the method's orchestration and logging without actual file I/O.
    """
    # Arrange
    builder = CommunityTemplateBuilder(mock_config_manager, mock_repository_metadata)
    builder.repo_path = tmp_path / f".{mock_config_manager.config.git.host}"
    builder.bug_issue_to_save = builder.repo_path / "BUG_ISSUE.md"
    caplog.set_level("INFO")

    with patch("osa_tool.operations.docs.community_docs_generation.community.save_sections") as mock_save_sections:
        mock_save_sections.return_value = None

        # Act
        builder.build_bug_issue()

        # Assert
        mock_save_sections.assert_called_once()
        assert "BUG_ISSUE.md successfully generated in folder" in caplog.text


@pytest.mark.parametrize(
    "method_name, expected_log",
    [
        ("build_code_of_conduct", "Error while generating CODE_OF_CONDUCT.md"),
        ("build_pull_request", "Error while generating PULL_REQUEST_TEMPLATE.md"),
        ("build_documentation_issue", "Error while generating DOCUMENTATION_ISSUE.md"),
        ("build_feature_issue", "Error while generating FEATURE_ISSUE.md"),
        ("build_bug_issue", "Error while generating BUG_ISSUE.md"),
    ],
)
def test_builder_methods_log_errors_on_exception(
    method_name, expected_log, mock_config_manager, mock_repository_metadata, sourcerank_with_repo_tree, caplog
):
    """
    Tests that builder methods log appropriate error messages when exceptions occur.
    
    This test method verifies that specific CommunityTemplateBuilder methods log
    expected error messages to the ERROR log level when they encounter exceptions
    during execution. It uses parameterized test cases to cover multiple builder
    methods and their corresponding error messages.
    
    Args:
        method_name: Name of the CommunityTemplateBuilder method to test.
        expected_log: Expected error message substring to find in the logs.
        mock_config_manager: Mock configuration manager for the builder.
        mock_repository_metadata: Mock repository metadata for the builder.
        sourcerank_with_repo_tree: Factory fixture to create SourceRank instance.
        caplog: Pytest fixture for capturing log messages.
    
    Why:
        The test ensures that when a builder method fails (e.g., due to a mocked exception),
        it properly logs an error message. This is important for debugging and monitoring
        the documentation generation process.
    
    Returns:
        None
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder = CommunityTemplateBuilder(mock_config_manager, mock_repository_metadata)
    builder.sourcerank = sourcerank
    caplog.set_level("ERROR")

    with patch(
        "osa_tool.operations.docs.community_docs_generation.community.save_sections",
        side_effect=Exception("save failed"),
    ):
        # Act
        method = getattr(builder, method_name)
        method()

        # Assert
        assert any(
            expected_log in message for message in caplog.messages
        ), f"Expected log message '{expected_log}' not found in logs: {caplog.messages}"
