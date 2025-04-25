from pathlib import Path

import pytest

from osa_tool.readmegen.prompts.prompts_article_config import PromptArticleLoader


@pytest.fixture
def mock_prompts_file(tmp_path) -> Path:
    prompts_file = tmp_path / "prompts_article.toml"
    prompts_file.write_text("""
    [prompts]
    file_summary = "Test file summary"
    pdf_summary = "Test PDF summary"
    overview = "Test overview"
    content = "Test content"
    algorithms = "Test algorithms"
    """.strip())
    return prompts_file


def test_prompt_loader_reads_mock_file(monkeypatch, mock_prompts_file):
    # Arrange
    monkeypatch.setattr(
        PromptArticleLoader,
        "_get_prompts_path",
        staticmethod(lambda: str(mock_prompts_file))
    )
    loader = PromptArticleLoader()
    # Act
    prompts = loader.prompts
    # Assert
    assert prompts.file_summary == "Test file summary"
    assert prompts.pdf_summary == "Test PDF summary"
    assert prompts.overview == "Test overview"
    assert prompts.content == "Test content"
    assert prompts.algorithms == "Test algorithms"
