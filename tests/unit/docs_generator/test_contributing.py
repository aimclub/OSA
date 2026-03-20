import os
from unittest.mock import patch

from osa_tool.operations.docs.community_docs_generation.contributing import ContributingBuilder
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_contributing_builder_initialization(mock_config_manager, mock_repository_metadata):
    """
    Verifies the correct initialization of the ContributingBuilder class and its attributes.
    
    This test ensures that the builder is properly instantiated with the provided configuration
    and metadata, and that all derived attributes (such as paths, URLs, and loaded templates)
    are correctly set and structured. It validates the internal state and configuration
    to confirm the builder is ready for generating contributing documentation.
    
    Args:
        mock_config_manager: A mocked configuration manager providing repository settings.
        mock_repository_metadata: A mocked metadata object containing repository information.
    
    Returns:
        None.
    """
    # Arrange
    builder = ContributingBuilder(mock_config_manager, mock_repository_metadata)

    # Assert
    assert builder.repo_url == mock_config_manager.config.git.repository
    assert builder.metadata == mock_repository_metadata

    assert isinstance(builder.sourcerank, SourceRank)

    assert builder.url_path.startswith("https://")
    assert builder.url_path.endswith("/")
    assert "tree/" in builder.branch_path

    assert builder.template_path.endswith("contributing.toml")
    assert builder.file_to_save.endswith("CONTRIBUTING.md")
    assert os.path.basename(os.path.dirname(builder.file_to_save)) == ".github"
    expected_repo_path = os.path.join(os.getcwd(), builder.repo_url.split("/")[-1], ".github")
    assert builder.repo_path == expected_repo_path

    template = builder.load_template()
    assert isinstance(template, dict)
    for key in ["introduction", "guide", "before_pull_request", "acknowledgements"]:
        assert key in template

    assert builder._template == template


def test_introduction_property(mock_config_manager, mock_repository_metadata):
    """
    Tests the introduction property of the ContributingBuilder class.
    
    This test verifies that the introduction property correctly incorporates key repository details—specifically the repository name and the issues URL—into the generated introductory text. This ensures the documentation builder produces a properly formatted and context-aware introduction for contribution guidelines.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used for testing.
        mock_repository_metadata: A mocked repository metadata instance containing repository details.
    
    Returns:
        None.
    """
    # Arrange
    builder = ContributingBuilder(mock_config_manager, mock_repository_metadata)

    # Act
    intro_text = builder.introduction

    # Assert
    assert mock_repository_metadata.name in intro_text
    assert builder.issues_url in intro_text


def test_guide_property(mock_config_manager, mock_repository_metadata):
    """
    Tests the guide property of the ContributingBuilder class.
    
    This test verifies that the `guide` property correctly incorporates the builder's URL path and the repository name into the generated guide text. It ensures the property constructs the guide content as expected for documentation generation.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used for testing.
        mock_repository_metadata: A mocked repository metadata instance containing repository details.
    
    Returns:
        None.
    """
    # Arrange
    builder = ContributingBuilder(mock_config_manager, mock_repository_metadata)

    # Act
    guide_text = builder.guide

    # Assert
    assert builder.url_path in guide_text
    assert mock_repository_metadata.name in guide_text


def test_before_pr_property(mock_config_manager, mock_repository_metadata):
    """
    Tests the `before_pr` property of the ContributingBuilder class.
    
    This test verifies that the `before_pr` property correctly composes its output by checking that it contains expected components from the builder instance. Specifically, it ensures the property includes the repository name, documentation, readme, and tests sections.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used for testing.
        mock_repository_metadata: A mocked repository metadata instance containing repository details.
    
    Returns:
        None.
    """
    # Arrange
    builder = ContributingBuilder(mock_config_manager, mock_repository_metadata)

    # Act
    before_pr_text = builder.before_pr

    # Assert
    assert mock_repository_metadata.name in before_pr_text
    assert builder.documentation in before_pr_text
    assert builder.readme in before_pr_text
    assert builder.tests in before_pr_text


def test_documentation_with_docs_presence_true(
    mock_config_manager, mock_repository_metadata, sourcerank_with_repo_tree
):
    """
    Tests the documentation property when documentation is present.
    
    This test verifies that the documentation section generated by the builder
    includes a reference to documentation, either via a 'docs/' directory path
    or via the repository's homepage URL. The test ensures the builder correctly
    identifies and reports available documentation sources when the repository
    tree indicates documentation is present.
    
    Args:
        mock_config_manager: Mock configuration manager.
        mock_repository_metadata: Mock repository metadata.
        sourcerank_with_repo_tree: Factory fixture to create a SourceRank instance configured with a mock repository tree.
    
    Returns:
        None
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = ContributingBuilder(mock_config_manager, mock_repository_metadata)
    builder.sourcerank = sourcerank

    # Act
    doc_section = builder.documentation

    # Assert
    assert "docs/" in doc_section or builder.metadata.homepage_url in doc_section


def test_documentation_with_docs_presence_false_and_no_homepage(
    mock_config_manager, mock_repository_metadata, sourcerank_with_repo_tree
):
    """
    Tests the documentation property when docs_presence is False and homepage_url is empty.
    
    This test verifies that the ContributingBuilder's documentation property returns an empty string when there are no documentation files present (docs_presence is False) and no homepage URL is provided. This ensures that the documentation section is correctly omitted in the generated output under these conditions.
    
    Args:
        mock_config_manager: Mock configuration manager.
        mock_repository_metadata: Mock repository metadata.
        sourcerank_with_repo_tree: Factory fixture to create a SourceRank instance with a given repository tree.
    
    Returns:
        An empty string, representing the generated documentation section.
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = ContributingBuilder(mock_config_manager, mock_repository_metadata)
    builder.sourcerank = sourcerank
    builder.metadata.homepage_url = ""

    # Act
    doc_section = builder.documentation

    # Assert
    assert doc_section == ""


def test_readme_with_readme_presence_true(mock_config_manager, mock_repository_metadata, sourcerank_with_repo_tree):
    """
    Tests the readme property when a README file is present in the repository.
    
    This test verifies that the ContributingBuilder's readme property correctly
    identifies and includes README information when the repository contains a
    README file. The test uses a mock repository tree that includes a README file
    to ensure the builder extracts and reports its presence.
    
    Args:
        mock_config_manager: Mock configuration manager for the builder.
        mock_repository_metadata: Mock repository metadata.
        sourcerank_with_repo_tree: Factory fixture to create a SourceRank instance
            with given repository tree data.
    
    Returns:
        None
    
    Why:
    This test ensures the builder's readme property functions correctly in the
    positive case—when a README file exists. It validates that the property
    does not miss the file and properly indicates its presence in the output,
    which is crucial for accurate documentation generation.
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = ContributingBuilder(mock_config_manager, mock_repository_metadata)
    builder.sourcerank = sourcerank

    # Act
    readme_section = builder.readme

    # Assert
    assert "README" in readme_section


def test_readme_with_readme_presence_false(mock_config_manager, mock_repository_metadata, sourcerank_with_repo_tree):
    """
    Tests that the readme property returns an empty string when README presence is false.
    
    This test verifies the behavior of the ContributingBuilder.readme property
    when the repository's SourceRank indicates no README file is present.
    It ensures that the property correctly handles the absence of a README by returning an empty string,
    which is important for downstream processes that may rely on this default behavior.
    
    Args:
        mock_config_manager: Mock configuration manager for the builder.
        mock_repository_metadata: Mock repository metadata for the builder.
        sourcerank_with_repo_tree: Factory fixture to create a SourceRank instance
            with given repository tree data.
    
    Returns:
        None
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = ContributingBuilder(mock_config_manager, mock_repository_metadata)
    builder.sourcerank = sourcerank

    # Act
    readme_section = builder.readme

    # Assert
    assert readme_section == ""


def test_tests_property_with_tests_presence(mock_config_manager, mock_repository_metadata, sourcerank_with_repo_tree):
    """
    Tests the 'tests' property when tests are present in the repository.
    
    This method verifies that the ContributingBuilder's 'tests' property correctly
    identifies and reports the presence of test files or directories when they exist
    in the repository structure. It uses a mock repository tree containing test
    directories or files to simulate a real repository scenario.
    
    Args:
        mock_config_manager: Mock configuration manager for the builder.
        mock_repository_metadata: Mock repository metadata for the builder.
        sourcerank_with_repo_tree: Factory fixture to create SourceRank instance
            with given repository tree data.
    
    Returns:
        None: This is a test method that performs assertions.
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = ContributingBuilder(mock_config_manager, mock_repository_metadata)
    builder.sourcerank = sourcerank

    # Act
    tests_section = builder.tests

    # Assert
    assert "tests/" in tests_section or "test" in tests_section.lower()
    assert tests_section != ""


def test_tests_property_without_tests_presence(
    mock_config_manager, mock_repository_metadata, sourcerank_with_repo_tree
):
    """
    Tests that the `tests` property returns an empty string when no tests are present in the repository tree.
    
    This test verifies that the `ContributingBuilder.tests` property correctly handles the absence of test files or directories. It ensures that when the repository tree contains no test-related entries, the property returns an empty string rather than `None` or raising an error.
    
    Args:
        mock_config_manager: Mock configuration manager used to instantiate the ContributingBuilder.
        mock_repository_metadata: Mock repository metadata used to instantiate the ContributingBuilder.
        sourcerank_with_repo_tree: Factory fixture that creates a SourceRank instance configured with a given mock repository tree.
    
    Returns:
        None
    """
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)

    builder = ContributingBuilder(mock_config_manager, mock_repository_metadata)
    builder.sourcerank = sourcerank

    # Act
    tests_section = builder.tests

    # Assert
    assert tests_section == ""


def test_acknowledgements_property(mock_config_manager, mock_repository_metadata):
    """
    Verifies that the acknowledgements property of the ContributingBuilder returns a non-empty string.
    This test ensures the builder correctly generates acknowledgements content, which is a required section for repository documentation.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the builder.
        mock_repository_metadata: A mocked repository metadata instance used to initialize the builder.
    
    Returns:
        None: This is a test method and does not return a value.
    """
    # Arrange
    builder = ContributingBuilder(mock_config_manager, mock_repository_metadata)

    # Act
    acknowledgements = builder.acknowledgements

    # Assert
    assert isinstance(acknowledgements, str)
    assert len(acknowledgements) > 0


def test_build_creates_dir_and_saves_file(mock_config_manager, mock_repository_metadata, tmp_path, caplog):
    """
    Verifies that the build method correctly creates the target directory and saves the contributing file.
    
    This test ensures the ContributingBuilder's build method creates the required .github directory,
    calls the necessary helper functions to assemble and clean the CONTRIBUTING.md file, and logs the success.
    
    Args:
        mock_config_manager: A mocked configuration manager instance.
        mock_repository_metadata: A mocked repository metadata instance.
        tmp_path: A pytest fixture providing a temporary directory path.
        caplog: A pytest fixture to capture log messages.
    
    Why:
        The test validates that the builder properly sets up the directory structure and file path,
        invokes the section-saving and formatting helpers, and confirms successful generation via logs.
        This is important to guarantee the automated documentation generation works as intended in the OSA Tool.
    """
    # Arrange
    builder = ContributingBuilder(mock_config_manager, mock_repository_metadata)
    builder.repo_path = tmp_path / ".github"
    builder.file_to_save = builder.repo_path / "CONTRIBUTING.md"
    caplog.set_level("INFO")

    with (
        patch("osa_tool.operations.docs.community_docs_generation.contributing.save_sections") as mock_save_sections,
        patch(
            "osa_tool.operations.docs.community_docs_generation.contributing.remove_extra_blank_lines"
        ) as mock_remove_blank_lines,
    ):
        mock_save_sections.return_value = None
        mock_remove_blank_lines.return_value = None

        # Act
        builder.build()

        # Assert
        assert builder.repo_path.exists()
        mock_save_sections.assert_called_once()
        mock_remove_blank_lines.assert_called_once_with(builder.file_to_save)
        assert f"CONTRIBUTING.md successfully generated in folder {builder.repo_path}" in caplog.text


def test_build_handles_exception_and_logs_error(mock_config_manager, mock_repository_metadata, caplog):
    """
    Verifies that the build method correctly handles exceptions and logs an error message.
    
    This test ensures that when an unexpected exception occurs during the file generation process, the error is caught and a descriptive message is recorded in the logs. Specifically, it tests that ContributingBuilder.build catches unexpected exceptions and logs an appropriate error, preventing silent failures.
    
    Args:
        mock_config_manager: A mocked configuration manager instance.
        mock_repository_metadata: A mocked repository metadata instance.
        caplog: The pytest fixture used to capture log output.
    
    Steps:
        1. Arrange: Creates a ContributingBuilder instance and sets the log level to capture ERROR logs.
        2. Act: Patches os.path.exists to raise an exception, then calls builder.build.
        3. Assert: Verifies that the expected error message appears in the captured logs.
    """
    # Arrange
    builder = ContributingBuilder(mock_config_manager, mock_repository_metadata)
    caplog.set_level("ERROR")

    with (patch("os.path.exists", side_effect=Exception("test error")),):
        # Act
        builder.build()

        # Assert
        assert "Error while generating CONTRIBUTING.md" in caplog.text
