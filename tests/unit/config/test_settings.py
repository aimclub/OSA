import pathlib
from argparse import Namespace
from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from osa_tool.config.settings import (
    ConfigManager,
    GitSettings,
    ModelGroupSettings,
    ModelSettings,
    Settings,
    PaperAnalysisSettings,
    PaperVerificationSettings,
    WorkflowSettings,
)


def _write_task_models_config(tmp_path) -> str:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        """
[git]
repository = "https://github.com/testuser/testrepo"

[llm]
rate_limit = 5
base_url = "https://api.openai.com/v1"
encoder = "cl100k_base"
host_name = "https://api.openai.com/v1"
localhost = "http://localhost:11434/"
model = "default-model"
path = "generate"
temperature = 0.05
max_tokens = 4096
context_window = 16385
top_p = 0.95
max_retries = 3
allowed_providers = ["openai"]
fallback_models = ["fallback-model"]
system_prompt = "You are a helpful assistant."

[llm.for_docstring_gen]
model = "docstring-model"

[llm.for_readme_gen]
model = "readme-model"

[llm.for_repository_quality]
model = "quality-model"

[llm.for_paper_claims]
model = "claims-model"

[llm.for_paper_verification]
model = "verification-model"

[paper_analysis]
output_dir = "configured-analysis"
only_high_medium_verifiability = false
hide_low_confidence = false

[paper_analysis.paper_claims]
pages_per_chunk = 7
max_retries = 4
dedup_batch_size = 19

[paper_analysis.verification]
batch_size = 20
candidate_file_limit = 4
source_snippet_max_lines = 120
repository_tree_max_paths = 160
csv_file_limit = 3

[workflows]
pep8_tool = "flake8"
""",
        encoding="utf-8",
    )
    return str(config_file)


def _make_config_args(config_file: str, **overrides) -> Namespace:
    args = {
        "config_file": config_file,
        "repository": "https://github.com/testuser/testrepo",
        "use_single_model": False,
        "model_docstring": None,
        "model_readme": None,
        "model_general": None,
        "model_repository_quality": None,
        "model_paper_claims": None,
        "model_paper_verification": None,
    }
    args.update(overrides)
    return Namespace(**args)


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
        config.llm.for_general_tasks,
        config.llm.for_repository_quality,
        config.llm.for_paper_claims,
        config.llm.for_paper_verification,
    ]:
        if task_model:
            assert isinstance(task_model, ModelSettings)

    assert isinstance(config.workflows, WorkflowSettings)
    assert isinstance(config.workflows.generate_workflows, bool)
    assert config.workflows.pep8_tool in ["flake8", "pylint"]

    assert config.prompts is not None
    assert isinstance(config.paper_analysis, PaperAnalysisSettings)


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
                "fallback_models": ["gpt-oss-120b", "claude-haiku-4.5"],
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
                "fallback_models": ["gpt-oss-120b", "claude-haiku-4.5"],
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
                "fallback_models": ["gpt-oss-120b", "claude-haiku-4.5"],
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
                "fallback_models": ["gpt-oss-120b", "claude-haiku-4.5"],
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
    assert settings.llm.for_general_tasks is None
    assert settings.llm.for_repository_quality is None
    assert settings.llm.for_paper_claims is None
    assert settings.llm.for_paper_verification is None


def test_config_manager_get_model_settings(mock_config_manager):
    # Arrange
    mock_config = mock_config_manager

    # Act
    default_settings = mock_config.get_model_settings("default")
    docstring_settings = mock_config.get_model_settings("docstring")
    readme_settings = mock_config.get_model_settings("readme")
    general_settings = mock_config.get_model_settings("general")
    quality_settings = mock_config.get_model_settings("repository_quality")
    paper_claim_settings = mock_config.get_model_settings("paper_claims")
    verification_settings = mock_config.get_model_settings("paper_verification")

    # Assert
    assert isinstance(default_settings, ModelSettings)

    if docstring_settings:
        assert isinstance(docstring_settings, ModelSettings)
    if readme_settings:
        assert isinstance(readme_settings, ModelSettings)
    if general_settings:
        assert isinstance(general_settings, ModelSettings)
    assert isinstance(quality_settings, ModelSettings)
    assert isinstance(paper_claim_settings, ModelSettings)
    assert isinstance(verification_settings, ModelSettings)


def test_config_manager_routes_docstring_to_task_model(tmp_path):
    manager = ConfigManager(_make_config_args(_write_task_models_config(tmp_path)))

    assert manager.get_model_settings("docstring").model == "docstring-model"
    assert manager.get_model_settings("readme").model == "readme-model"
    assert manager.get_model_settings("repository_quality").model == "quality-model"
    assert manager.get_model_settings("paper_claims").model == "claims-model"
    assert manager.get_model_settings("paper_verification").model == "verification-model"


def test_config_manager_applies_docstring_cli_model_override(tmp_path):
    manager = ConfigManager(
        _make_config_args(
            _write_task_models_config(tmp_path),
            model_docstring="cli-docstring-model",
        )
    )

    assert manager.get_model_settings("docstring").model == "cli-docstring-model"
    assert manager.get_model_settings("readme").model == "readme-model"


def test_config_manager_applies_paper_cli_model_override(tmp_path):
    manager = ConfigManager(
        _make_config_args(
            _write_task_models_config(tmp_path),
            model_paper_verification="cli-verification-model",
        )
    )

    assert manager.get_model_settings("paper_verification").model == "cli-verification-model"
    assert manager.get_model_settings("paper_claims").model == "claims-model"


def test_config_manager_loads_typed_paper_analysis_settings(tmp_path):
    manager = ConfigManager(_make_config_args(_write_task_models_config(tmp_path)))

    settings = manager.get_paper_analysis_settings()

    assert settings.output_dir.name == "configured-analysis"
    assert settings.only_high_medium_verifiability is False
    assert settings.hide_low_confidence is False
    assert settings.paper_claims.pages_per_chunk == 7
    assert settings.paper_claims.dedup_batch_size == 19
    assert settings.verification.batch_size == 20
    assert settings.verification.candidate_file_limit == 4


def test_paper_verification_settings_reject_batch_size_above_external_limit():
    with pytest.raises(ValidationError, match="less than or equal to 50"):
        PaperVerificationSettings(batch_size=51)


def test_config_manager_uses_default_model_when_single_model_is_enabled(tmp_path):
    manager = ConfigManager(_make_config_args(_write_task_models_config(tmp_path), use_single_model=True))

    assert manager.get_model_settings("docstring").model == "default-model"
    assert manager.get_model_settings("readme").model == "default-model"


def test_config_manager_applies_based_on_date_cli_override(tmp_path):
    # Arrange & Act
    manager = ConfigManager(_make_config_args(_write_task_models_config(tmp_path), based_on_date="17.05.2023"))

    # Assert
    assert manager.config.git.based_on_date == datetime(2023, 5, 17, tzinfo=timezone.utc)


def test_config_manager_reads_based_on_date_from_config_file(tmp_path):
    # Arrange
    config_file = _write_task_models_config(tmp_path)
    content = pathlib.Path(config_file).read_text(encoding="utf-8")
    pathlib.Path(config_file).write_text(
        content.replace(
            '[git]\nrepository = "https://github.com/testuser/testrepo"',
            '[git]\nrepository = "https://github.com/testuser/testrepo"\nbased_on_date = 2021-01-01',
        ),
        encoding="utf-8",
    )

    # Act
    manager = ConfigManager(_make_config_args(config_file))

    # Assert
    assert manager.config.git.based_on_date == datetime(2021, 1, 1, tzinfo=timezone.utc)


def test_config_manager_cli_based_on_date_overrides_config_file(tmp_path):
    # Arrange
    config_file = _write_task_models_config(tmp_path)
    content = pathlib.Path(config_file).read_text(encoding="utf-8")
    pathlib.Path(config_file).write_text(
        content.replace(
            '[git]\nrepository = "https://github.com/testuser/testrepo"',
            '[git]\nrepository = "https://github.com/testuser/testrepo"\nbased_on_date = 2021-01-01',
        ),
        encoding="utf-8",
    )

    # Act
    manager = ConfigManager(_make_config_args(config_file, based_on_date="2024-03-01"))

    # Assert
    assert manager.config.git.based_on_date == datetime(2024, 3, 1, tzinfo=timezone.utc)


def test_git_settings_invalid_based_on_date():
    # Act & Assert
    with pytest.raises(ValidationError, match="Cannot parse date"):
        GitSettings(repository="https://github.com/testuser/testrepo", based_on_date="the day before yesterday")


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
    invalid_url = "htttp://not-a-valid-url"

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        GitSettings(repository=invalid_url)

    assert "Provided URL is not correct" in str(exc_info.value)


def test_git_settings_not_existing_path():
    # Arrange
    not_existing_path = "not_existing_path"

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        GitSettings(repository=not_existing_path)

    assert "does not exist" in str(exc_info.value)


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
        "fallback_models": ["gpt-oss-120b", "claude-haiku-4.5"],
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
    assert "claude-haiku-4.5" in model_settings.fallback_models


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
        "fallback_models": ["gpt-oss-120b", "claude-haiku-4.5"],
        "system_prompt": "You are a helpful assistant.",
    }

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        ModelSettings(**model_data)

    assert "temperature" in str(exc_info.value)
