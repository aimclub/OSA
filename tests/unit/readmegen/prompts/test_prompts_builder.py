from unittest.mock import MagicMock, patch

import pytest

from osa_tool.readmegen.context.files_contents import FileContext
from osa_tool.readmegen.prompts.prompts_builder import PromptBuilder


@pytest.fixture
def mock_config_loader():
    """
    Creates a mock configuration loader with a predefined repository URL.
    
    Returns:
        MagicMock: A mock object with a `config.git.repository` attribute set to
        "https://github.com/test/repo".
    """
    mock = MagicMock()
    mock.config.git.repository = "https://github.com/test/repo"
    return mock


@pytest.fixture
def mock_metadata():
    """
    Creates a mock metadata object for testing purposes.
    
    This function returns a MagicMock instance with predefined
    attributes `name` and `description` set to example values.
    
    Returns:
        MagicMock: A mock object with `name` set to "TestProject" and
        `description` set to "Test project description".
    """
    mock = MagicMock()
    mock.name = "TestProject"
    mock.description = "Test project description"
    return mock


@pytest.fixture
def file_contexts():
    """
    Method Name: file_contexts
    
    Returns a list of FileContext objects representing example Python files.
    
    Parameters
    ----------
    None
    
    Returns
    -------
    list[FileContext]
        A list containing two FileContext instances, each with a name, path, and content
        representing simple Python scripts.
    """
    return [
        FileContext(name="file1.py", path="src/file1.py", content="print('hello')"),
        FileContext(name="file2.py", path="src/file2.py", content="print('world')"),
    ]


@pytest.fixture(autouse=True)
def patch_dependencies(mock_metadata):
    """
    Patch dependencies for tests by mocking various functions and classes used in the prompts builder.
    
    Parameters
    ----------
    mock_metadata
        The metadata object to be returned by the mocked `load_data_metadata` function.
    
    Returns
    -------
    None
        This fixture yields control to the test and does not return a value.
    
    Notes
    -----
    This fixture automatically patches the following components from `osa_tool.readmegen.prompts.prompts_builder`:
    
    * `load_data_metadata` – returns the supplied `mock_metadata`.
    * `extract_readme_content` – returns a static string `"README content"`.
    * `parse_folder_name` – returns the string `"repo"`.
    * `SourceRank` – its `tree` attribute is set to `"repo/tree"`.
    * `PromptBuilder.load_prompts` – its side effect returns predefined dictionaries for
      `prompts.toml` and `prompts_article.toml` paths, and an empty dictionary for other paths.
    
    The fixture is marked with `@pytest.fixture(autouse=True)` so it is applied automatically to all tests in the module.
    """
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
                    "overview": "Article for {project_name} | Files: {files_summary} | PDF: {pdf_summary} | Readme: {readme_content}",
                    "content": "Article content: {project_name}, {files_summary}, {pdf_summary} | Readme: {readme_content}",
                    "algorithms": "Algo: {project_name} | {files_content} | {pdf_summary} | Readme: {readme_content}",
                }
            else:
                return {}

        mock_load_prompts.side_effect = side_effect

        yield


def test_get_prompt_preanalysis(mock_config_loader):
    """
    Test that PromptBuilder.get_prompt_preanalysis returns a prompt containing expected sections.
    
    Parameters
    ----------
    mock_config_loader
    
    Returns
    -------
    None
    """
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    # Act
    prompt = builder.get_prompt_preanalysis()
    # Assert
    assert "Tree: repo/tree" in prompt
    assert "Readme: README content" in prompt


def test_get_prompt_core_features(mock_config_loader, file_contexts):
    """
    Test that PromptBuilder.get_prompt_core_features returns a prompt containing core features.
    
    This test verifies that the prompt generated by PromptBuilder includes the project name,
    the list of keys, and the names of the files provided in the file contexts. It
    creates a PromptBuilder instance using a mock configuration loader, calls
    `get_prompt_core_features` with the supplied file contexts, and asserts that
    expected substrings are present in the resulting prompt string.
    
    Parameters
    ----------
    mock_config_loader
        Mock configuration loader used to instantiate PromptBuilder.
    file_contexts
        Contexts of files to be passed to get_prompt_core_features.
    
    Returns
    -------
    None
    """
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    # Act
    prompt = builder.get_prompt_core_features(file_contexts)
    # Assert
    assert "Project: TestProject" in prompt
    assert "Keys: " in prompt
    assert "file1.py" in prompt


def test_get_prompt_overview(mock_config_loader):
    """
    Test that PromptBuilder.get_prompt_overview returns a prompt containing the project name and the specified core features.
    
    Args:
        mock_config_loader: A mock configuration loader used to instantiate PromptBuilder.
    
    Returns:
        None
    """
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    core_features = "Fast, Modular"
    # Act
    prompt = builder.get_prompt_overview(core_features)
    # Assert
    assert "Name: TestProject" in prompt
    assert "Features: Fast, Modular" in prompt


def test_get_prompt_getting_started(mock_config_loader, file_contexts):
    """
    Test that PromptBuilder.get_prompt_getting_started returns a prompt containing the
    project name, a list of examples, and the names of the provided file contexts.
    
    Parameters
    ----------
    mock_config_loader : object
        A mock configuration loader used to instantiate the PromptBuilder.
    file_contexts : list
        A list of file context objects that are passed to the builder to generate the
        prompt.
    
    Returns
    -------
    None
        This function is a test and does not return a value; it asserts that the
        generated prompt contains expected substrings.
    """
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    # Act
    prompt = builder.get_prompt_getting_started(file_contexts)
    # Assert
    assert "Proj: TestProject" in prompt
    assert "Examples: " in prompt
    assert "file2.py" in prompt


def test_get_prompt_files_summary(mock_config_loader, file_contexts):
    """
    Test that PromptBuilder.get_prompt_files_summary correctly includes file names in the generated prompt.
    
    Parameters
    ----------
    mock_config_loader
        A mock configuration loader used to instantiate the PromptBuilder.
    file_contexts
        A collection of file contexts that the prompt should summarize.
    
    Returns
    -------
    None
    
    This test constructs a PromptBuilder with the provided configuration loader, calls its
    get_prompt_files_summary method with the supplied file contexts, and asserts that the
    returned prompt string contains the expected header ("Files: ") and at least one
    file name ("file1.py").
    """
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    # Act
    prompt = builder.get_prompt_files_summary(file_contexts)
    # Assert
    assert "Files: " in prompt
    assert "file1.py" in prompt


def test_get_prompt_pdf_summary(mock_config_loader):
    """
    Test that PromptBuilder.get_prompt_pdf_summary correctly formats a prompt with PDF content.
    
    Parameters
    ----------
    mock_config_loader
        A mock configuration loader used to instantiate the PromptBuilder.
    
    Returns
    -------
    None
        This test does not return a value; it asserts that the generated prompt contains the expected substring.
    """
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    # Act
    prompt = builder.get_prompt_pdf_summary("PDF content here")
    # Assert
    assert "PDF: PDF content here" in prompt


def test_get_prompt_overview_article(mock_config_loader):
    """
    Test that PromptBuilder.get_prompt_overview_article returns a prompt containing the project name, summary file, and PDF file.
    
    Args:
        mock_config_loader: A mock configuration loader used to instantiate PromptBuilder.
    
    Returns:
        None
    """
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    # Act
    prompt = builder.get_prompt_overview_article("Summary A", "PDF B")
    # Assert
    assert "Article for TestProject" in prompt
    assert "Files: Summary A" in prompt
    assert "PDF: PDF B" in prompt


def test_get_prompt_content_article(mock_config_loader):
    """
    Test that PromptBuilder.get_prompt_content_article returns a prompt containing the provided identifiers.
    
    Parameters
    ----------
    mock_config_loader : object
        A fixture providing a mock configuration loader used to instantiate PromptBuilder.
    
    Returns
    -------
    None
    """
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    print(builder.prompts_article["content"])
    # Act
    prompt = builder.get_prompt_content_article("FS", "PDF Summary")
    # Assert
    assert "FS" in prompt
    assert "PDF Summary" in prompt


def test_get_prompt_algorithms_article(mock_config_loader, file_contexts):
    """
    Test that PromptBuilder.get_prompt_algorithms_article returns a prompt containing algorithm
    information and file context.
    
    Parameters
    ----------
    mock_config_loader : object
        Mock configuration loader used to instantiate PromptBuilder.
    file_contexts : list
        List of file context objects to be passed to the method.
    
    Returns
    -------
    None
    
    This test verifies that the generated prompt includes the algorithm name, file names, code
    snippets, and the specified summary type.
    """
    # Arrange
    builder = PromptBuilder(mock_config_loader)
    # Act
    prompt = builder.get_prompt_algorithms_article(file_contexts, "PDF SUM")
    # Assert
    assert "Algo: TestProject" in prompt
    assert "file1.py" in prompt
    assert "print('hello')" in prompt
    assert "PDF SUM" in prompt
