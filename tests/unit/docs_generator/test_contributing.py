from unittest import mock

import pytest

from osa_tool.docs_generator.contributing import ContributingBuilder


@pytest.fixture
def builder(config_loader):
    """
    Builds a :class:`ContributingBuilder` instance with mocked dependencies.
    
    The function patches the ``SourceRank`` class and the ``load_data_metadata`` function
    from the ``osa_tool.docs_generator.contributing`` module to provide deterministic
    values for documentation presence checks and repository metadata. These mocks
    simulate a repository that contains a ``CONTRIBUTING.md`` file, a ``README.md``,
    and tests, and provide default metadata such as the repository name and default
    branch. After setting up the mocks, the function returns a new
    ``ContributingBuilder`` initialized with the supplied ``config_loader``.
    
    Parameters
    ----------
    config_loader
        The configuration loader to be passed to the :class:`ContributingBuilder`.
    
    Returns
    -------
    ContributingBuilder
        A ``ContributingBuilder`` instance initialized with the provided
        ``config_loader`` and the mocked environment.
    """
    with (
        mock.patch("osa_tool.docs_generator.contributing.SourceRank") as MockSourceRank,
        mock.patch("osa_tool.docs_generator.contributing.load_data_metadata") as mock_metadata,
    ):
        mock_rank = MockSourceRank.return_value
        mock_rank.docs_presence.return_value = True
        mock_rank.readme_presence.return_value = True
        mock_rank.tests_presence.return_value = True
        mock_rank.tree = "docs/CONTRIBUTING.md\nREADME.md\ntests/"

        mock_metadata.return_value = mock.Mock(default_branch="main", name="TestProject", homepage_url=None)

        return ContributingBuilder(config_loader)


@mock.patch("osa_tool.docs_generator.contributing.save_sections")
@mock.patch("osa_tool.docs_generator.contributing.logger")
@mock.patch("osa_tool.docs_generator.contributing.os.makedirs")
@mock.patch("osa_tool.docs_generator.contributing.remove_extra_blank_lines")
def test_build_contributing(mock_remove_blank_lines, mock_makedirs, mock_logger, mock_save, builder):
    """
    Test the build process of the CONTRIBUTING.md generator.
    
    This test verifies that the `build` method of the provided `builder` instance
    correctly assembles the content sections, creates the necessary directories,
    saves the file, and logs a success message. It uses mocked dependencies to
    ensure that the interactions occur as expected without performing actual file
    system or logging operations.
    
    Parameters
    ----------
    mock_remove_blank_lines : mock
        Mock for the `remove_extra_blank_lines` function; its return value is
        set to `None` to simulate no-op behavior.
    mock_makedirs : mock
        Mock for `os.makedirs`; used to confirm that the repository path is
        created.
    mock_logger : mock
        Mock for the module-level `logger`; used to verify that an info log
        entry is made after successful generation.
    mock_save : mock
        Mock for the `save_sections` function; used to assert that the
        generated content is written to the correct file path.
    builder : object
        Instance of the contributing documentation builder under test. It
        exposes attributes such as `introduction`, `guide`, `before_pr`,
        `acknowledgements`, `file_to_save`, and `repo_path`.
    
    Returns
    -------
    None
        This function does not return a value; it performs assertions on the
        mocked interactions to validate the build process.
    """
    # Arrange
    expected_content = "\n".join(
        [
            builder.introduction,
            builder.guide,
            builder.before_pr,
            builder.acknowledgements,
        ]
    )
    mock_remove_blank_lines.return_value = None
    # Act
    builder.build()
    # Assert
    mock_save.assert_called_once_with(expected_content, builder.file_to_save)
    mock_makedirs.assert_called_once_with(builder.repo_path)
    mock_logger.info.assert_called_once_with(f"CONTRIBUTING.md successfully generated in folder {builder.repo_path}")


def test_introduction_content(builder):
    """
    Test that the introduction content is correctly generated.
    
        Parameters
        ----------
        builder
            The builder object used to generate the introduction content. It must
            expose an `introduction` attribute containing the rendered text and an
            `issues_url` attribute that should appear in the introduction.
    
        Returns
        -------
        None
    
        Raises
        ------
        AssertionError
            If the introduction does not contain the expected project name or
            issues URL, or if it contains a disallowed string.
    """
    # Act
    intro = builder.introduction
    # Assert
    assert "Thanks for creating a Pull Request" not in intro
    assert "TestProject" in intro
    assert builder.issues_url in intro


def test_guide_content(builder):
    """
    Test that the guide content contains expected project name and URL path.
    
    Args:
        builder: The builder object providing the `guide` string and the `url_path` attribute.
    
    Returns:
        None
    
    This method retrieves the guide text from the builder and verifies that it includes
    the string "TestProject" as well as the builder's URL path. It uses assertions
    to ensure the guide content is correct.
    """
    # Act
    guide = builder.guide
    # Assert
    assert "TestProject" in guide
    assert builder.url_path in guide


def test_before_pr_content(builder):
    """
    Test that the `before_pr` content contains the expected project information.
    
    This test retrieves the `before_pr` string from the provided `builder` object and
    verifies that it includes the project name, documentation, README, and test
    sections. The assertions ensure that the generated content is correctly
    assembled before a pull request is created.
    
    Parameters
    ----------
    builder
        An object that provides the following attributes:
        - `before_pr`: the string content to be inspected.
        - `documentation`: a string expected to appear in `before_pr`.
        - `readme`: a string expected to appear in `before_pr`.
        - `tests`: a string expected to appear in `before_pr`.
    
    Returns
    -------
    None
        The function performs assertions and does not return a value.
    """
    # Act
    before_pr = builder.before_pr
    # Assert
    assert "TestProject" in before_pr
    assert builder.documentation in before_pr
    assert builder.readme in before_pr
    assert builder.tests in before_pr


def test_documentation_link(builder):
    """
    Test that the builder's documentation includes a link to CONTRIBUTING.md or an example URL.
    
    Parameters
    ----------
    builder
        The builder instance whose documentation property is to be checked.
    
    Returns
    -------
    None
        This function does not return a value; it raises an AssertionError if the condition is not met.
    """
    # Act
    docs = builder.documentation
    # Assert
    assert "docs/CONTRIBUTING.md" in docs or "example.com" in docs


def test_readme_link(builder):
    """
    Test that the builder's readme includes the README.md link.
    
    Args:
        builder: The builder instance whose readme property is to be checked.
    
    Returns:
        None
    """
    # Act
    readme = builder.readme
    # Assert
    assert "README.md" in readme


def test_tests_link(builder):
    """
    Test that the builder's tests path includes 'tests/'.
    
    Args:
        builder: The builder instance whose tests attribute is to be checked.
    
    Returns:
        None
    """
    # Act
    tests = builder.tests
    # Assert
    assert "tests/" in tests


def test_acknowledgements_content(builder):
    """
    Test that the acknowledgements content is a non-empty string.
    
    Parameters
    ----------
    builder
        The object under test that provides an `acknowledgements` attribute.
    
    Returns
    -------
    None
        This function does not return a value; it asserts conditions on the
        acknowledgements content.
    """
    # Act
    ack = builder.acknowledgements
    # Assert
    assert isinstance(ack, str)
    assert len(ack) > 0
