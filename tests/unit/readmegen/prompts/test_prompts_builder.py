import pytest

from osa_tool.readmegen.context.files_contents import FileContext


def test_serialize_file_contexts(prompt_builder):
    # Arrange
    files = [
        FileContext(name="file1.py", path="src/file1.py", content="print('hello')"),
        FileContext(name="file2.py", path="src/file2.py", content="print('world')"),
    ]

    # Act
    result = prompt_builder.serialize_file_contexts(files)

    # Assert
    expected = "### file1.py (src/file1.py)\nprint('hello')\n\n### file2.py (src/file2.py)\nprint('world')"
    assert result == expected


def test_load_prompts_valid(prompt_builder):
    # Arrange
    prompt_path = prompt_builder.readme_prompt_path

    # Act
    prompts = prompt_builder.load_prompts(prompt_path)

    # Assert
    assert "preanalysis" in prompts
    assert "Based on the provided information" in prompts["core_features"]


def test_load_prompts_missing_file(prompt_builder):
    # Assert
    with pytest.raises(FileNotFoundError):
        prompt_builder.load_prompts("non_existing_file.toml")


def test_get_prompt_preanalysis(prompt_builder):
    # Act
    prompt = prompt_builder.get_prompt_preanalysis()

    # Assert
    assert "Sample README" in prompt
    assert str(prompt_builder.tree) in prompt


def test_get_prompt_core_features(prompt_builder):
    # Arrange
    key_files = [FileContext(name="main.py", path="src/main.py", content="print('hi')")]

    # Act
    prompt = prompt_builder.get_prompt_core_features(key_files)

    # Assert
    assert "Sample README" in prompt
    assert "main.py" in prompt
    assert prompt_builder.metadata.name in prompt


def test_get_prompt_overview(prompt_builder):
    # Act
    prompt = prompt_builder.get_prompt_overview(core_features="some features")

    # Assert
    assert "some features" in prompt
    assert prompt_builder.metadata.description in prompt


def test_get_prompt_getting_started(prompt_builder):
    # Arrange
    example_files = [FileContext(name="example.py", path="examples/example.py", content="print('example')")]

    # Act
    prompt = prompt_builder.get_prompt_getting_started(example_files)

    # Assert
    assert "example.py" in prompt
    assert "Sample README" in prompt


def test_get_prompt_files_summary(prompt_builder):
    # Arrange
    files = [FileContext(name="a.py", path="src/a.py", content="print('a')")]

    # Act
    prompt = prompt_builder.get_prompt_files_summary(files)

    # Assert
    assert "a.py" in prompt
    assert "Sample README" in prompt


def test_get_prompt_pdf_summary(prompt_builder):
    # Act
    prompt = prompt_builder.get_prompt_pdf_summary("PDF text here")

    # Assert
    assert "PDF text here" in prompt


def test_get_prompt_overview_article(prompt_builder):
    # Act
    prompt = prompt_builder.get_prompt_overview_article("files summary", "pdf summary")

    # Assert
    assert "files summary" in prompt
    assert "pdf summary" in prompt
    assert "Sample README" in prompt


def test_get_prompt_content_article(prompt_builder):
    # Act
    prompt = prompt_builder.get_prompt_content_article("files summary", "pdf summary")

    # Assert
    assert "files summary" in prompt
    assert "pdf summary" in prompt


def test_get_prompt_algorithms_article(prompt_builder):
    # Arrange
    files = [FileContext(name="algo.py", path="src/algo.py", content="def foo(): pass")]

    # Act
    prompt = prompt_builder.get_prompt_algorithms_article(files, "pdf summary")

    # Assert
    assert "algo.py" in prompt
    assert "pdf summary" in prompt


def test_get_prompt_refine_readme(prompt_builder):
    # Arrange
    new_sections = "## Installation\n\nnew install\n\n## Usage\n\nusage"

    # Act
    prompt = prompt_builder.get_prompt_refine_readme(new_sections)

    # Assert
    assert "Sample README" in prompt
    assert "## Installation" in prompt
