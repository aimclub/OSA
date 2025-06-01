from pathlib import Path

import pytest

from osa_tool.readmegen.prompts.prompts_config import PromptLoader


@pytest.fixture
def mock_prompts_file(tmp_path) -> Path:
    prompts_file = tmp_path / "prompts.toml"
    prompts_file.write_text(
        """
    [prompts]
    preanalysis = "Test preanalysis template"
    core_features = "Test core features template"
    overview = "Test overview template"
    getting_started = "Test getting started template"
    """.strip()
    )
    return prompts_file


def test_prompt_loader_reads_mock_file(monkeypatch, mock_prompts_file):
    # Arrange
    monkeypatch.setattr(
        PromptLoader, "_get_prompts_path", staticmethod(lambda: str(mock_prompts_file))
    )
    # Act
    prompts = PromptLoader().prompts
    # Assert
    assert prompts["preanalysis"] == "Test preanalysis template"
    assert prompts["core_features"] == "Test core features template"
    assert prompts["overview"] == "Test overview template"
    assert prompts["getting_started"] == "Test getting started template"
