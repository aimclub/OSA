import pytest
from pydantic import ValidationError

from osa_tool.config.settings import (
    ConfigManager,
    GitSettings,
    ModelSettings,
    ModelGroupSettings,
    Settings,
    WorkflowSettings,
)


def test_config_manager_success(mock_config_manager):
    # Arrange
    config = mock_config_manager.config

    # Assert
    assert isinstance(config, Settings)

    assert isinstance(config.git, GitSettings)
    assert config.git.repository
    assert config.git.name
    assert config.git.host
    assert config.git.full_name

    assert isinstance(config.llm, ModelGroupSettings)
    assert isinstance(config.llm.default, ModelSettings)
    assert config.llm.default.model
    assert config.llm.default.temperature <= 1

    for task_model in [
        config.llm.for_docstring_gen,
        config.llm.for_readme_gen,
        config.llm.for_validation,
        config.llm.for_general_tasks,
    ]:
        if task_model:
            assert isinstance(task_model, ModelSettings)

    assert isinstance(config.workflows, WorkflowSettings)
    assert isinstance(config.workflows.generate_workflows, bool)
    assert config.workflows.pep8_tool in ["flake8", "pylint"]

    assert config.prompts is not None


def test_config_manager_file_not_found(monkeypatch):
    # Arrange
    monkeypatch.setattr("osa_tool.config.settings.build_config_path", lambda: "/nonexistent/config.toml")

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="Default configuration file not found: /nonexistent/config.toml"):
        ConfigManager()


def test_config_manager_invalid_pep8_tool():
    bad_config = {
        "git": {"repository": "https://github.com/org/repo"},
        "llm": {
            "default": {
                "api": "openai",
                "rate_limit": 5,
                "base_url": "https://api.openai.com/v1",
                "encoder": "cl100k_base",
                "host_name": "https://api.openai.com/v1",
                "localhost": "http://localhost:11434/",
                "model": "gpt-3.5-turbo",
                "path": "generate",
                "temperature": 0.05,
                "max_tokens": 4096,
                "context_window": 16385,
                "top_p": 0.95,
                "max_retries": 3,
                "allowed_providers": ["openai"],
                "system_prompt": "You are a helpful assistant.",
            }
        },
        "workflows": {
            "pep8_tool": "badtool",
        },
    }

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        Settings.model_validate(bad_config)

    error_str = str(exc_info.value)
    assert "pep8_tool" in error_str
    assert "flake8" in error_str or "pylint" in error_str


def test_config_manager_without_llm_default():
    bad_config = {
        "git": {"repository": "https://github.com/org/repo"},
        "llm": {
            "for_docstring_gen": {
                "api": "openai",
                "rate_limit": 5,
                "base_url": "https://api.openai.com/v1",
                "encoder": "cl100k_base",
                "host_name": "https://api.openai.com/v1",
                "localhost": "http://localhost:11434/",
                "model": "gpt-3.5-turbo",
                "path": "generate",
                "temperature": 0.05,
                "max_tokens": 4096,
                "context_window": 16385,
                "top_p": 0.95,
                "max_retries": 3,
                "allowed_providers": ["openai"],
                "system_prompt": "You are a helpful assistant.",
            }
        },
        "workflows": {
            "pep8_tool": "flake8",
        },
    }

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        Settings.model_validate(bad_config)

    assert "default" in str(exc_info.value)


def test_model_group_settings_partial_tasks():
    config_data = {
        "git": {"repository": "https://github.com/org/repo"},
        "llm": {
            "default": {
                "api": "openai",
                "rate_limit": 5,
                "base_url": "https://api.openai.com/v1",
                "encoder": "cl100k_base",
                "host_name": "https://api.openai.com/v1",
                "localhost": "http://localhost:11434/",
                "model": "gpt-3.5-turbo",
                "path": "generate",
                "temperature": 0.05,
                "max_tokens": 4096,
                "context_window": 16385,
                "top_p": 0.95,
                "max_retries": 3,
                "allowed_providers": ["openai"],
                "system_prompt": "You are a helpful assistant.",
            },
            "for_readme_gen": {
                "api": "openai",
                "rate_limit": 5,
                "base_url": "https://api.openai.com/v1",
                "encoder": "cl100k_base",
                "host_name": "https://api.openai.com/v1",
                "localhost": "http://localhost:11434/",
                "model": "gpt-4",
                "path": "generate",
                "temperature": 0.1,
                "max_tokens": 4096,
                "context_window": 16385,
                "top_p": 0.95,
                "max_retries": 3,
                "allowed_providers": ["openai"],
                "system_prompt": "You are a helpful assistant.",
            },
        },
        "workflows": {
            "pep8_tool": "flake8",
        },
    }

    # Act
    settings = Settings.model_validate(config_data)

    # Assert
    assert isinstance(settings.llm, ModelGroupSettings)
    assert isinstance(settings.llm.default, ModelSettings)
    assert settings.llm.default.model == "gpt-3.5-turbo"
    assert isinstance(settings.llm.for_readme_gen, ModelSettings)
    assert settings.llm.for_readme_gen.model == "gpt-4"
    assert settings.llm.for_docstring_gen is None
    assert settings.llm.for_validation is None
    assert settings.llm.for_general_tasks is None


def test_config_manager_get_model_settings(mock_config_manager):
    # Arrange
    mock_config = mock_config_manager

    # Act
    default_settings = mock_config.get_model_settings("default")
    docstring_settings = mock_config.get_model_settings("docstring")
    readme_settings = mock_config.get_model_settings("readme")
    validation_settings = mock_config.get_model_settings("validation")
    general_settings = mock_config.get_model_settings("general")

    # Assert
    assert isinstance(default_settings, ModelSettings)

    if docstring_settings:
        assert isinstance(docstring_settings, ModelSettings)
    if readme_settings:
        assert isinstance(readme_settings, ModelSettings)
    if validation_settings:
        assert isinstance(validation_settings, ModelSettings)
    if general_settings:
        assert isinstance(general_settings, ModelSettings)


def test_git_settings_validation():
    # Arrange
    repo_url = "https://github.com/testuser/testrepo"

    # Act
    git_settings = GitSettings(repository=repo_url)

    # Assert
    assert git_settings.repository == repo_url
    assert git_settings.host == "github"
    assert git_settings.name == "testrepo"
    assert git_settings.full_name == "testuser/testrepo"


def test_git_settings_invalid_url():
    # Arrange
    invalid_url = "not-a-valid-url"

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        GitSettings(repository=invalid_url)

    assert "Provided URL is not correct" in str(exc_info.value)


def test_git_settings_valid_url_with_special_characters():
    # Arrange
    repo_url = "https://github.com/test-user/test_repo-123"

    # Act
    git_settings = GitSettings(repository=repo_url)

    # Assert
    assert git_settings.repository == repo_url
    assert git_settings.host == "github"
    assert git_settings.name == "test_repo-123"
    assert git_settings.full_name == "test-user/test_repo-123"


def test_workflow_settings_defaults():
    # Arrange & Act
    workflow_settings = WorkflowSettings()

    # Assert
    assert workflow_settings.generate_workflows is False
    assert workflow_settings.include_tests is True
    assert workflow_settings.include_black is True
    assert workflow_settings.include_pep8 is True
    assert workflow_settings.include_autopep8 is False
    assert workflow_settings.include_fix_pep8 is False
    assert workflow_settings.include_pypi is False
    assert workflow_settings.python_versions == ["3.9", "3.10"]
    assert workflow_settings.pep8_tool == "flake8"
    assert workflow_settings.use_poetry is False
    assert workflow_settings.branches == ["main", "master"]
    assert workflow_settings.codecov_token is False
    assert workflow_settings.include_codecov is True


def test_model_settings_validation():
    # Arrange
    model_data = {
        "api": "openai",
        "rate_limit": 5,
        "base_url": "https://api.openai.com/v1",
        "encoder": "cl100k_base",
        "host_name": "https://api.openai.com/v1",
        "localhost": "http://localhost:11434/",
        "model": "gpt-3.5-turbo",
        "path": "generate",
        "temperature": 0.05,
        "max_tokens": 4096,
        "context_window": 16385,
        "top_p": 0.95,
        "max_retries": 3,
        "allowed_providers": ["openai"],
        "system_prompt": "You are a helpful assistant.",
    }

    # Act
    model_settings = ModelSettings(**model_data)

    # Assert
    assert model_settings.api == "openai"
    assert model_settings.model == "gpt-3.5-turbo"
    assert model_settings.temperature == 0.05
    assert model_settings.max_tokens == 4096
    assert "openai" in model_settings.allowed_providers


def test_model_settings_invalid_temperature():
    # Arrange
    model_data = {
        "api": "openai",
        "rate_limit": 5,
        "base_url": "https://api.openai.com/v1",
        "encoder": "cl100k_base",
        "host_name": "https://api.openai.com/v1",
        "localhost": "http://localhost:11434/",
        "model": "gpt-3.5-turbo",
        "path": "generate",
        "temperature": -0.1,
        "max_tokens": 4096,
        "context_window": 16385,
        "top_p": 0.95,
        "max_retries": 3,
        "allowed_providers": ["openai"],
        "system_prompt": "You are a helpful assistant.",
    }

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        ModelSettings(**model_data)

    assert "temperature" in str(exc_info.value)
