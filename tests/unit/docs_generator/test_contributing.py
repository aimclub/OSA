from unittest import mock

import pytest

from osa_tool.docs_generator.contributing import ContributingBuilder


@pytest.fixture
def builder(config_loader):
    with mock.patch("osa_tool.docs_generator.contributing.SourceRank") as MockSourceRank, \
         mock.patch("osa_tool.docs_generator.contributing.load_data_metadata") as mock_metadata:
        mock_rank = MockSourceRank.return_value
        mock_rank.docs_presence.return_value = True
        mock_rank.readme_presence.return_value = True
        mock_rank.tests_presence.return_value = True
        mock_rank.tree = "docs/CONTRIBUTING.md\nREADME.md\ntests/"

        mock_metadata.return_value = mock.Mock(
            default_branch="main",
            name="TestProject",
            homepage_url=None
        )

        return ContributingBuilder(config_loader)


@mock.patch("osa_tool.docs_generator.contributing.save_sections")
@mock.patch("osa_tool.docs_generator.contributing.logger")
@mock.patch("osa_tool.docs_generator.contributing.os.makedirs")
@mock.patch("osa_tool.docs_generator.contributing.remove_extra_blank_lines")
def test_build_contributing(mock_remove_blank_lines, mock_makedirs, mock_logger, mock_save, builder):
    # Arrange
    expected_content = "\n".join([
        builder.introduction,
        builder.guide,
        builder.before_pr,
        builder.acknowledgements
    ])
    mock_remove_blank_lines.return_value = None
    # Act
    builder.build()
    # Assert
    mock_save.assert_called_once_with(expected_content, builder.file_to_save)
    mock_makedirs.assert_called_once_with(builder.repo_path)
    mock_logger.info.assert_called_once_with(f"CONTRIBUTING.md successfully generated in folder {builder.repo_path}")


def test_introduction_content(builder):
    # Act
    intro = builder.introduction
    # Assert
    assert "Thanks for creating a Pull Request" not in intro
    assert "TestProject" in intro
    assert builder.issues_url in intro


def test_guide_content(builder):
    # Act
    guide = builder.guide
    # Assert
    assert "TestProject" in guide
    assert builder.url_path in guide


def test_before_pr_content(builder):
    # Act
    before_pr = builder.before_pr
    # Assert
    assert "TestProject" in before_pr
    assert builder.documentation in before_pr
    assert builder.readme in before_pr
    assert builder.tests in before_pr


def test_documentation_link(builder):
    # Act
    docs = builder.documentation
    # Assert
    assert "docs/CONTRIBUTING.md" in docs or "example.com" in docs


def test_readme_link(builder):
    # Act
    readme = builder.readme
    # Assert
    assert "README.md" in readme


def test_tests_link(builder):
    # Act
    tests = builder.tests
    # Assert
    assert "tests/" in tests


def test_acknowledgements_content(builder):
    # Act
    ack = builder.acknowledgements
    # Assert
    assert isinstance(ack, str)
    assert len(ack) > 0
