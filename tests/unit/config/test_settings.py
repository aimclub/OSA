import pytest
from pydantic import ValidationError

from osa_tool.config.settings import (
    ConfigManager,
    GitSettings,
    ModelGroupSettings,
    ModelSettings,
    Settings,
    WorkflowSettings,
)


def test_config_manager_success(mock_config_manager):
    """
    Verifies that the configuration manager successfully initializes and populates the settings object with valid data.
    
    This test ensures that the configuration hierarchy—including Git, LLM (Large Language Model), and workflow settings—is correctly structured and contains the expected default values and types. The test validates the integrity of the configuration after the manager loads it, confirming that all required components are present and correctly typed.
    
    Args:
        mock_config_manager: A mocked instance of the configuration manager providing access to the settings object.
    
    Why:
        This test is crucial because the configuration manager is responsible for loading and structuring all tool settings. If the configuration is malformed or missing required fields, subsequent operations (like documentation generation or validation) will fail. The test ensures the manager correctly builds the Settings object from the provided configuration source.
    """
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
    """
    Tests that ConfigManager raises a FileNotFoundError when the configuration file does not exist.
    
    This test ensures that the ConfigManager constructor properly validates the existence of the default configuration file and raises an appropriate error if it is missing, preventing silent failures in configuration loading.
    
    Args:
        monkeypatch: A pytest fixture used to mock the configuration file path to a non-existent location.
    
    Raises:
        FileNotFoundError: If the configuration file is not found at the expected path. The error message includes the missing file path.
    """
    # Arrange
    monkeypatch.setattr("osa_tool.config.settings.build_config_path", lambda: "/nonexistent/config.toml")

    # Act & Assert
    with pytest.raises(FileNotFoundError, match="Default configuration file not found: /nonexistent/config.toml"):
        ConfigManager()


def test_config_manager_invalid_pep8_tool():
    """
    Verifies that the configuration manager raises a validation error when an invalid PEP8 tool is provided.
    
    This test case constructs a configuration dictionary with an unsupported value for the 'pep8_tool' field within the workflows section. It ensures that the Settings model validation fails and that the resulting error message correctly identifies the problematic field and suggests valid alternatives like 'flake8' or 'pylint'.
    
    Args:
        None
    
    Returns:
        None
    
    Why:
        The test ensures that the Settings model properly validates the 'pep8_tool' field, rejecting unsupported values. This is important to prevent runtime errors by catching invalid configuration early and guiding users toward valid tool choices.
    """
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
    """
    Verifies that the configuration manager raises a ValidationError when the 'default' LLM configuration is missing.
    
    This test case constructs a configuration dictionary containing 'git', 'workflows', and a specific LLM profile ('for_docstring_gen'), but intentionally omits the required 'default' LLM key. It then validates that the Settings model correctly identifies this omission and raises an error containing the word 'default'.
    
    WHY: The 'default' LLM configuration is required because it serves as the fallback profile when no specific LLM profile is referenced, ensuring the system has a baseline configuration for LLM operations.
    
    Args:
        None
    
    Raises:
        ValidationError: If the configuration validation does not fail as expected when the 'default' LLM key is missing.
    """
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
    """
    Verifies that the ModelGroupSettings can be partially populated from a configuration dictionary.
    
    This test ensures that when a configuration contains settings for only a subset of specific tasks (e.g., 'default' and 'for_readme_gen'), the Settings object correctly validates the provided models while leaving the unspecified task-specific fields as None. This is important because the tool supports multiple, optional workflows, and each may have its own LLM configuration; the system must handle incomplete configurations gracefully without requiring every task to be defined.
    
    Args:
        None
    
    Returns:
        None
    """
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
    assert settings.llm.for_validation is None
    assert settings.llm.for_general_tasks is None


def test_config_manager_get_model_settings(mock_config_manager):
    """
    Verifies that the ConfigManager correctly retrieves ModelSettings for various task types.
    
    This test ensures that the `get_model_settings` method returns valid ModelSettings instances for different configuration keys including default, docstring, readme, validation, and general settings. It validates that the returned objects are of the correct type, handling cases where certain settings may be optional (None) by only asserting type when they are present.
    
    Args:
        mock_config_manager: A mocked instance of the ConfigManager used to retrieve model settings. This fixture provides a controlled environment to test configuration retrieval without relying on actual configuration files.
    
    Why:
        This test is crucial because the ConfigManager is responsible for providing appropriate model configurations for different documentation tasks (e.g., generating docstrings, READMEs, validation reports). Ensuring it returns correctly typed settings for each key guarantees that downstream tasks receive valid configuration objects, preventing runtime errors and misconfigurations.
    """
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
    """
    Verifies that the GitSettings class correctly validates and parses a given repository URL.
        
    The test ensures that when a GitSettings object is initialized with a repository URL, it correctly extracts and assigns the host, repository name, and full repository name to its respective attributes. This validation is crucial for the OSA Tool's repository analysis pipeline, as accurate parsing of repository URLs ensures proper handling of source code locations during automated documentation and enhancement operations.
    
    Args:
        None
        
    Returns:
        None
    """
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
    """
    Verifies that providing an invalid URL to the GitSettings constructor raises a ValidationError.
    
    The test ensures that the GitSettings class performs URL validation during initialization and returns the expected error message when the repository URL format is incorrect.
    
    Args:
        invalid_url: A string representing an invalid repository URL used to trigger validation.
    
    Raises:
        ValidationError: If the provided repository URL is not a valid format. The test checks that the error message contains "Provided URL is not correct".
    
    Why:
        This test validates that the GitSettings class properly enforces URL format constraints, preventing the use of malformed repository URLs that could cause errors in subsequent Git operations.
    """
    # Arrange
    invalid_url = "not-a-valid-url"

    # Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        GitSettings(repository=invalid_url)

    assert "Provided URL is not correct" in str(exc_info.value)


def test_git_settings_valid_url_with_special_characters():
    """
    Verifies that the GitSettings class correctly parses a valid repository URL containing special characters.
    
    This test case ensures that when a GitSettings object is initialized with a URL containing hyphens and underscores, the repository, host, name, and full_name attributes are correctly extracted and assigned. The test validates the parsing logic for common special characters used in repository names and user identifiers.
    
    Args:
        None
    
    Returns:
        None
    """
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
    """
    Verifies that a new instance of WorkflowSettings is initialized with the correct default values.
        
    This test ensures that all configuration flags, tool selections, and version lists
    within the WorkflowSettings object are set to their expected initial states.
    This is important to guarantee that the OSA Tool's workflow generation starts with a consistent and predictable configuration, preventing unintended behavior in downstream automation processes.
    
    Args:
        None
    
    The following class fields are verified with their expected default values:
        generate_workflows: Boolean flag indicating if workflows should be generated. Default is False.
        include_tests: Boolean flag indicating if test steps are included. Default is True.
        include_black: Boolean flag indicating if Black formatting checks are included. Default is True.
        include_pep8: Boolean flag indicating if PEP8 linting is included. Default is True.
        include_autopep8: Boolean flag indicating if autopep8 formatting is included. Default is False.
        include_fix_pep8: Boolean flag indicating if automatic PEP8 fixes are included. Default is False.
        include_pypi: Boolean flag indicating if PyPI deployment steps are included. Default is False.
        python_versions: List of Python version strings to be supported. Default is ["3.9", "3.10"].
        pep8_tool: String identifying the tool used for PEP8 linting. Default is "flake8".
        use_poetry: Boolean flag indicating if Poetry is used for dependency management. Default is False.
        branches: List of git branch names that trigger the workflow. Default is ["main", "master"].
        codecov_token: Boolean or string indicating the presence of a Codecov token. Default is False.
        include_codecov: Boolean flag indicating if Codecov reporting is included. Default is True.
    """
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
    """
    Verifies that the ModelSettings class correctly validates and initializes model configuration data.
        
    This test case ensures that when a dictionary of model parameters is passed to the ModelSettings constructor, the resulting object correctly stores and provides access to attributes such as API provider, model name, temperature, token limits, and provider-specific settings. The test validates both required fields and optional configuration parameters to confirm proper handling of the full configuration dictionary.
    
    Args:
        None
    
    Why:
        This test is necessary to guarantee that the ModelSettings class reliably processes a complete set of configuration parameters—including API endpoints, token limits, fallback models, and system prompts—without errors. It ensures that the class correctly initializes all attributes from a dictionary input, which is critical for the OSA Tool's ability to dynamically load and validate model configurations from external sources (e.g., configuration files or user inputs).
    """
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
    """
    Verifies that the ModelSettings class raises a ValidationError when an invalid temperature value is provided.
    
    This test case ensures that the model configuration validates the temperature field, specifically checking that a negative value (outside the typical 0.0 to 2.0 range) triggers the expected validation error. The test uses a sample model configuration dictionary with a temperature of -0.1 to trigger the validation failure.
    
    Args:
        None
    
    Raises:
        ValidationError: If the temperature value provided to ModelSettings is invalid.
    """
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
