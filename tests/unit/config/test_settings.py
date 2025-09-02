import pytest
from pydantic import ValidationError

from osa_tool.config.settings import Settings, GitSettings, ModelSettings, WorkflowSettings, ConfigLoader


def test_config_loader_success(mock_config_loader):
    # Arrange
    config = mock_config_loader.config

    # Assert
    assert isinstance(config, Settings)

    assert isinstance(config.git, GitSettings)
    assert config.git.repository
    assert config.git.name
    assert config.git.host
    assert config.git.full_name

    assert isinstance(config.llm, ModelSettings)
    assert config.llm.model
    assert config.llm.temperature <= 1

    assert isinstance(config.workflows, WorkflowSettings)
    assert isinstance(config.workflows.generate_workflows, bool)
    assert config.workflows.pep8_tool in ["flake8", "pylint"]


def test_config_loader_file_not_found(monkeypatch):
    # Arrange
    monkeypatch.setattr("osa_tool.config.settings.build_config_path", lambda: "/nonexistent/config.toml")

    # Assert
    with pytest.raises(FileNotFoundError):
        ConfigLoader()._get_config_path()

    with pytest.raises(FileNotFoundError, match="Configuration file .* not found"):
        ConfigLoader()


def test_config_loader_invalid_pep8_tool():
    bad_config = {
        "git": {"repository": "https://github.com/org/repo"},
        "llm": {
            "api": "openai",
            "url": "https://api.openai.com/v1",
            "context_window": 4096,
            "encoder": "cl100k_base",
            "host_name": "https://api.openai.com/v1",
            "localhost": "http://localhost:11434/",
            "model": "gpt-3.5-turbo",
            "path": "generate",
            "temperature": 0.05,
            "tokens": 4096,
            "top_p": 0.95,
        },
        "workflows": {
            "pep8_tool": "badtool",
        },
    }

    with pytest.raises(ValidationError) as exc_info:
        Settings.model_validate(bad_config)

    assert "pep8_tool" in str(exc_info.value)
    assert "flake8" in str(exc_info.value)
    assert "pylint" in str(exc_info.value)
