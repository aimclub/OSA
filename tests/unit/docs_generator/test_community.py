from unittest import mock

import pytest

from osa_tool.docs_generator.community import CommunityTemplateBuilder


@pytest.fixture
def builder(config_loader):
    """
    Builds a `CommunityTemplateBuilder` instance with mocked dependencies for testing.
    
    Parameters
    ----------
    config_loader
        The configuration loader to be passed to the `CommunityTemplateBuilder`.
    
    Returns
    -------
    CommunityTemplateBuilder
        An instance of `CommunityTemplateBuilder` initialized with the provided `config_loader`. The method temporarily patches `SourceRank` and `load_data_metadata` to return predefined mock objects, ensuring that the builder operates with controlled test data.
    """
    with (
        mock.patch("osa_tool.docs_generator.community.SourceRank") as MockSourceRank,
        mock.patch("osa_tool.docs_generator.community.load_data_metadata") as mock_metadata,
    ):
        mock_rank = MockSourceRank.return_value
        mock_rank.contributing_presence.return_value = True
        mock_rank.docs_presence.return_value = True
        mock_rank.tree = ["docs/CONTRIBUTING.md"]

        mock_metadata.return_value = mock.Mock(default_branch="main", name="TestProject")

        return CommunityTemplateBuilder(config_loader)


@mock.patch("osa_tool.docs_generator.community.save_sections")
@mock.patch("osa_tool.docs_generator.community.logger")
def test_build_code_of_conduct(mock_logger, mock_save, builder):
    """
    Test that the builder correctly builds the code of conduct section and saves it.
    
    Parameters
    ----------
    mock_logger : mock
        Mocked logger used to verify that an info log is emitted.
    mock_save : mock
        Mocked save_sections function used to verify that the generated content is saved.
    builder : object
        Instance of the docs generator builder used to build the code of conduct.
    
    Returns
    -------
    None
        This test does not return a value; it asserts expected behavior.
    """
    # Act
    builder.build_code_of_conduct()
    expected_content = builder._template["code_of_conduct"]
    # Assert
    mock_save.assert_called_once_with(expected_content, builder.code_of_conduct_to_save)
    mock_logger.info.assert_called_once()


@mock.patch("osa_tool.docs_generator.community.save_sections")
@mock.patch("osa_tool.docs_generator.community.logger")
@mock.patch(
    "osa_tool.docs_generator.community.find_in_repo_tree",
    return_value="docs/CONTRIBUTING.md",
)
def test_build_pull_request(mock_find, mock_logger, mock_save, builder):
    """
    Test building a pull request.
    
    This test verifies that the `build_pull_request` method of the provided `builder` object correctly generates the pull request content and saves it using the `save_sections` function, while also logging the operation.
    
    Parameters
    ----------
    mock_find : mock
        Mock for the `find_in_repo_tree` function, configured to return the path to the CONTRIBUTING.md file.
    mock_logger : mock
        Mock for the logger used by the module.
    mock_save : mock
        Mock for the `save_sections` function that should be called with the generated content.
    builder : object
        Instance of the class under test, expected to have a `build_pull_request` method, a `_template` dictionary, and a `pr_to_save` attribute.
    
    Returns
    -------
    None
        This test does not return a value; it asserts that the expected interactions occur.
    """
    # Act
    builder.build_pull_request()
    contributing_url = f"https://github.com/user/TestProject/tree/main/docs/CONTRIBUTING.md"
    expected_content = builder._template["pull_request"].format(contributing_url=contributing_url)
    # Assert
    mock_save.assert_called_once_with(expected_content, builder.pr_to_save)
    mock_logger.info.assert_called_once()


@mock.patch("osa_tool.docs_generator.community.save_sections")
@mock.patch("osa_tool.docs_generator.community.logger")
def test_build_documentation_issue(mock_logger, mock_save, builder):
    """
    Test building documentation issue.
    
    This test verifies that the `build_documentation_issue` method of the
    `builder` instance generates the expected documentation content and that
    this content is saved correctly using the `save_sections` function. It also
    ensures that an informational log entry is produced during the process.
    
    Parameters
    ----------
    mock_logger : mock
        Mocked logger used to verify that an info log is emitted.
    mock_save : mock
        Mocked `save_sections` function used to verify that the content is
        saved with the correct arguments.
    builder : object
        Instance of the documentation builder under test.
    
    Returns
    -------
    None
    """
    # Act
    builder.build_documentation_issue()
    expected_content = builder._template["docs_issue"]
    # Assert
    mock_save.assert_called_once_with(expected_content, builder.docs_issue_to_save)
    mock_logger.info.assert_called_once()


@mock.patch("osa_tool.docs_generator.community.save_sections")
@mock.patch("osa_tool.docs_generator.community.logger")
def test_build_feature_issue(mock_logger, mock_save, builder):
    """
    Test building a feature issue.
    
    This test verifies that the `build_feature_issue` method of the builder
    produces the expected content and that the content is saved and logged
    appropriately. It uses mocked `save_sections` and `logger` to assert
    that the correct calls are made.
    
    Parameters
    ----------
    mock_logger : mock
        Mocked logger used to verify that an info message is logged.
    mock_save : mock
        Mocked save_sections function used to verify that the generated
        content is saved to the correct destination.
    builder : object
        Instance of the builder under test, which provides
        `build_feature_issue`, `_template`, `metadata`, and
        `feature_issue_to_save` attributes.
    
    Returns
    -------
    None
    """
    # Act
    builder.build_feature_issue()
    expected_content = builder._template["feature_issue"].format(project_name=builder.metadata.name)
    # Assert
    mock_save.assert_called_once_with(expected_content, builder.feature_issue_to_save)
    mock_logger.info.assert_called_once()


@mock.patch("osa_tool.docs_generator.community.save_sections")
@mock.patch("osa_tool.docs_generator.community.logger")
def test_build_bug_issue(mock_logger, mock_save, builder):
    """
    Test that the builder correctly constructs and saves a bug issue section.
    
    Parameters
    ----------
    mock_logger : mock
        Mocked logger used to verify that an info message is logged during the build process.
    mock_save : mock
        Mocked save_sections function used to verify that the generated bug issue content is saved.
    builder : object
        Instance of the builder under test, expected to have a `_template` dictionary, a `metadata.name` attribute, and a `bug_issue_to_save` attribute.
    
    Returns
    -------
    None
        This test does not return a value; it asserts that the builder behaves as expected by checking the calls to the mocked save function and logger.
    """
    # Act
    builder.build_bug_issue()
    expected_content = builder._template["bug_issue"].format(project_name=builder.metadata.name)
    # Assert
    mock_save.assert_called_once_with(expected_content, builder.bug_issue_to_save)
    mock_logger.info.assert_called_once()
