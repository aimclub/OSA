from unittest.mock import MagicMock, patch

import pytest

from osa_tool.readmegen.context.files_contents import FileContext
from osa_tool.readmegen.prompts.prompts_builder import PromptBuilder


@pytest.fixture
def mock_config_loader():
    mock = MagicMock()
    mock.config.git.repository = "https://github.com/test/repo"
    return mock


@pytest.fixture
def mock_metadata():
    mock = MagicMock()
    mock.name = "TestProject"
    mock.description = "Test project description"
    return mock


@pytest.fixture
def file_contexts():
    return [
        FileContext(name="file1.py", path="src/file1.py", content="print('hello')"),
        FileContext(name="file2.py", path="src/file2.py", content="print('world')"),
    ]


@pytest.fixture(autouse=True)
def patch_dependencies(mock_metadata):
    with (
        patch(
            "osa_tool.readmegen.prompts.prompts_builder.load_data_metadata",
            return_value=mock_metadata,
        ),
        patch(
            "osa_tool.readmegen.prompts.prompts_builder.extract_readme_content",
            return_value="README content",
        ),
        patch(
            "osa_tool.readmegen.prompts.prompts_builder.parse_folder_name",
            return_value="repo",
        ),
        patch("osa_tool.readmegen.prompts.prompts_builder.SourceRank") as mock_sourcerank,
        patch("osa_tool.readmegen.prompts.prompts_builder.PromptBuilder.load_prompts") as mock_load_prompts,
    ):
        mock_sourcerank.return_value.tree = "repo/tree"

        def side_effect(path):
            if "prompts.toml" in path:
                return {
                    "preanalysis": "Tree: {repository_tree} | Readme: {readme_content}",
                    "core_features": "Project: {project_name}, Meta: {metadata}, Readme: {readme_content}, Keys: {key_files_content}",
                    "overview": "Name: {project_name}, Desc: {description}, Readme: {readme_content}, Features: {core_features}",
                    "getting_started": "Proj: {project_name}, Readme: {readme_content}, Examples: {examples_files_content}",
                }
            elif "prompts_article.toml" in path:
                return {
                    "file_summary": "Files: {files_content}",
                    "pdf_summary": "PDF: {pdf_content}",
                    "overview": "Article for {project_name} | Files: {files_summary} | PDF: {pdf_summary}",
                    "content": "Article content: {project_name}, {files_content}, {pdf_summary}",
                    "algorithms": "Algo: {project_name} | {file_summary} | {pdf_summary}",
                }
            else:
                return {}

        mock_load_prompts.side_effect = side_effect

        yield


def test_get_prompt_preanalysis(mock_config_loader):
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    # Act
    prompt = builder.get_prompt_preanalysis()
    # Assert
    assert "Tree: repo/tree" in prompt
    assert "Readme: README content" in prompt


def test_get_prompt_core_features(mock_config_loader, file_contexts):
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    # Act
    prompt = builder.get_prompt_core_features(file_contexts)
    # Assert
    assert "Project: TestProject" in prompt
    assert "Keys: " in prompt
    assert "file1.py" in prompt


def test_get_prompt_overview(mock_config_loader):
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    core_features = "Fast, Modular"
    # Act
    prompt = builder.get_prompt_overview(core_features)
    # Assert
    assert "Name: TestProject" in prompt
    assert "Features: Fast, Modular" in prompt


def test_get_prompt_getting_started(mock_config_loader, file_contexts):
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    # Act
    prompt = builder.get_prompt_getting_started(file_contexts)
    # Assert
    assert "Proj: TestProject" in prompt
    assert "Examples: " in prompt
    assert "file2.py" in prompt


def test_get_prompt_files_summary(mock_config_loader, file_contexts):
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    # Act
    prompt = builder.get_prompt_files_summary(file_contexts)
    # Assert
    assert "Files: " in prompt
    assert "file1.py" in prompt


def test_get_prompt_pdf_summary(mock_config_loader):
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    # Act
    prompt = builder.get_prompt_pdf_summary("PDF content here")
    # Assert
    assert "PDF: PDF content here" in prompt


def test_get_prompt_overview_article(mock_config_loader):
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    # Act
    prompt = builder.get_prompt_overview_article("Summary A", "PDF B")
    # Assert
    assert "Article for TestProject" in prompt
    assert "Files: Summary A" in prompt
    assert "PDF: PDF B" in prompt


def test_get_prompt_content_article(mock_config_loader, file_contexts):
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    # Act
    prompt = builder.get_prompt_content_article(file_contexts, "PDF Summary")
    # Assert
    assert "file1.py" in prompt
    assert "PDF Summary" in prompt


def test_get_prompt_algorithms_article(mock_config_loader):
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    # Act
    prompt = builder.get_prompt_algorithms_article("FS", "PDF SUM")
    # Assert
    assert "Algo: TestProject" in prompt
    assert "FS" in prompt
    assert "PDF SUM" in prompt
