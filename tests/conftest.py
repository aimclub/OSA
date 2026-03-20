import os
from contextlib import ExitStack
from unittest.mock import Mock, patch, MagicMock

import pytest

from osa_tool.config.settings import Settings, GitSettings, ModelSettings, ModelGroupSettings, WorkflowSettings
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.prompts_builder import PromptLoader
from osa_tool.utils.utils import parse_folder_name
from tests.data_factory import DataFactory
from tests.utils.mocks.requests_mock import mock_requests_response

pytest_plugins = [
    "tests.utils.fixtures.about_generation",
    "tests.utils.fixtures.analytics_load_metadata",
    "tests.utils.fixtures.analytics_report_generator",
    "tests.utils.fixtures.analytics_sourcerank",
    "tests.utils.fixtures.models",
    "tests.utils.fixtures.osa_arguments_parser",
    "tests.utils.fixtures.osatreesitter",
    "tests.utils.fixtures.readmegen_context_article",
    "tests.utils.fixtures.readmegen_llm_service",
    "tests.utils.fixtures.readmegen_markdown_builder",
    "tests.utils.fixtures.readmegen_readme_refiner",
    "tests.utils.fixtures.scheduler",
    "tests.utils.fixtures.ui_plan_editor",
]


@pytest.fixture(scope="session")
def data_factory():
    """
    A session-scoped pytest fixture that provides an instance of the DataFactory.
    This fixture is session-scoped to ensure a single DataFactory instance is reused across all tests in the test session, promoting efficiency and consistent test data generation.
    
    Returns:
        DataFactory: An instance of the DataFactory class for generating test data.
    """
    return DataFactory()


# -------------------
# Config Manager Fixtures
# -------------------
@pytest.fixture
def mock_config_manager(data_factory, request):
    """
    Mock ConfigManager with dynamically generated test data.
    
    Args:
        data_factory: Factory that generates test settings data.
        request: Provides the platform parameter via its 'param' attribute; defaults to "github" if not specified.
    
    Returns:
        A mocked ConfigManager instance configured with generated settings.
    
    Why:
        This method creates a mock of the ConfigManager to isolate tests from real configuration and external dependencies (like API keys and tokens). It uses dynamically generated settings to ensure tests are reproducible and cover various platform scenarios without relying on live credentials or actual configuration files.
    """
    platform = getattr(request, "param", "github")
    test_settings = data_factory.generate_full_settings(platform)

    if isinstance(test_settings["llm"], dict) and "default" in test_settings["llm"]:
        default_llm_settings = test_settings["llm"]["default"]
        model_settings = ModelSettings(**default_llm_settings)

        model_group_settings = ModelGroupSettings(
            default=model_settings,
            for_docstring_gen=model_settings,
            for_readme_gen=model_settings,
            for_validation=model_settings,
            for_general_tasks=model_settings,
        )
    else:
        model_settings = ModelSettings(**test_settings["llm"])
        model_group_settings = ModelGroupSettings(
            default=model_settings,
            for_docstring_gen=model_settings,
            for_readme_gen=model_settings,
            for_validation=model_settings,
            for_general_tasks=model_settings,
        )

    settings = Settings(
        git=GitSettings(**test_settings["git"]),
        llm=model_group_settings,
        workflows=WorkflowSettings(**test_settings["workflows"]),
    )

    mock_manager = Mock()
    mock_manager.config = settings

    mock_manager.get_model_settings = Mock(return_value=model_settings)
    mock_manager.get_git_settings = Mock(return_value=settings.git)
    mock_manager.get_workflow_settings = Mock(return_value=settings.workflows)
    mock_manager.get_prompts = Mock(return_value=settings.prompts)

    os.environ["OPENAI_API_KEY"] = "fake-key-for-tests"
    os.environ["GIT_TOKEN"] = "fake_token"

    with patch("osa_tool.config.settings.ConfigManager", return_value=mock_manager):
        yield mock_manager


@pytest.fixture
def config_manager_with_updates(mock_config_manager):
    """
    Fixture for tests that need to modify configuration settings dynamically.
    
    This fixture returns an updater function that allows temporary modifications to a mock configuration manager's settings. It is designed to support test scenarios where specific configuration values (like LLM parameters or other sections) must be altered without permanently changing the underlying configuration.
    
    Args:
        mock_config_manager: A mock configuration manager object whose config attribute contains the settings to be updated.
    
    Returns:
        A function (updater) that accepts keyword arguments representing configuration sections and their new values. When called, this function applies the updates to the mock configuration manager and returns the modified manager.
    
    The updater function processes updates by section:
    - For the "llm" section, it handles nested updates for default settings and specific task settings (for_docstring_gen, for_readme_gen, for_validation, for_general_tasks). It merges new values into existing ModelSettings objects.
    - For other sections, it updates the entire section by merging new values into the existing section object and reinstantiating it with the updated dictionary.
    
    Why this approach? It allows tests to isolate configuration changes within a controlled scope, ensuring that modifications do not leak between tests and that the original configuration can be easily restored.
    """

    def updater(**kwargs):
        for section, values in kwargs.items():
            if hasattr(mock_config_manager.config, section):
                if section == "llm":
                    current_llm = mock_config_manager.config.llm
                    if "default" in values:
                        default_dict = current_llm.default.model_dump()
                        default_dict.update(values["default"])
                        current_llm.default = ModelSettings(**default_dict)
                    for task in ["for_docstring_gen", "for_readme_gen", "for_validation", "for_general_tasks"]:
                        if task in values and getattr(current_llm, task):
                            task_dict = getattr(current_llm, task).dict()
                            task_dict.update(values[task])
                            setattr(current_llm, task, ModelSettings(**task_dict))
                else:
                    current = getattr(mock_config_manager.config, section).dict()
                    updated = {**current, **values}
                    section_class = type(getattr(mock_config_manager.config, section))
                    setattr(mock_config_manager.config, section, section_class(**updated))
        return mock_config_manager

    return updater


# -------------------
# SourceRank Fixtures
# -------------------
@pytest.fixture
def mock_sourcerank(mock_config_manager, mock_parse_folder_name, data_factory):
    """
    Factory fixture to create SourceRank instances with patched methods.
    
    This fixture is used in testing to generate SourceRank objects with controlled,
    mocked dependencies and method behaviors. It allows flexible patching of external
    calls and internal methods, enabling isolated unit tests that focus on the
    SourceRank logic without relying on real filesystem operations or external services.
    
    Args:
        mock_config_manager: A mocked or fake configuration manager object to be
            passed to the SourceRank constructor.
        mock_parse_folder_name: A value or mock to be returned when
            `parse_folder_name` is called inside SourceRank.
        data_factory: A fixture that provides randomized or predefined return values
            for SourceRank's methods, used to simulate various behaviors.
    
    Returns:
        A factory function that, when called, returns a configured SourceRank instance
        with the specified patches and method overrides applied.
    
    The returned factory function accepts:
        repo_tree: If provided, replaces the return value of `get_repo_tree` with
            this value, simulating a specific repository structure.
        method_overrides: An optional dictionary mapping method names to desired
            return values. These override any random values generated by `data_factory`
            for those methods, allowing precise control over method behavior in tests.
    
    Inside the factory, an ExitStack manages multiple patch contexts, ensuring clean
    setup and teardown of mocks. After patching external dependencies, the SourceRank
    instance is created, and additional methods are replaced with MagicMock objects
    returning the values determined by `data_factory` and `method_overrides`.
    """

    def factory(repo_tree=None, method_overrides=None) -> SourceRank:
        overrides = method_overrides or {}
        random_methods = data_factory.random_source_rank_methods(force_overrides=overrides)

        patches = [
            patch(
                "osa_tool.tools.repository_analysis.sourcerank.parse_folder_name", return_value=mock_parse_folder_name
            ),
        ]

        if repo_tree is not None:
            patches.append(patch("osa_tool.tools.repository_analysis.sourcerank.get_repo_tree", return_value=repo_tree))

        with ExitStack() as stack:
            for p in patches:
                stack.enter_context(p)

            instance = SourceRank(mock_config_manager)

            for method_name, return_value in random_methods.items():
                mocked_method = MagicMock(return_value=return_value)
                setattr(instance, method_name, mocked_method)

            return instance

    return factory


# -------------------
# Prompts Fixtures
# -------------------
@pytest.fixture
def mock_prompts():
    """
    Initializes and returns a prompt loader instance for mocking purposes.
    
    This function is used to create a PromptLoader instance that can be utilized in testing or simulation environments where actual prompt loading from external sources is not required or desired. It provides a controlled, predictable object for scenarios such as unit tests, development sandboxes, or demonstrations.
    
    Returns:
        An instance of the PromptLoader class.
    """
    return PromptLoader()


# -------------------
# RepositoryMetadata Fixtures
# -------------------
@pytest.fixture
def repo_info(mock_config_manager):
    """
    Extracts repository metadata from the configuration manager.
    
    This method parses the git configuration to retrieve key repository identifiers and URLs, which are commonly needed for constructing API calls, generating documentation links, or performing repository operations.
    
    Args:
        mock_config_manager: The configuration manager object containing git settings. It is expected to have attributes for the repository's full name (owner/name), host platform, and repository URL.
    
    Returns:
        tuple: A tuple containing, in order: the platform host (e.g., 'github.com'), the repository owner, the repository name, and the full repository URL.
    """
    full_name = mock_config_manager.config.git.full_name
    owner, repo_name = full_name.split("/")
    repo_url = mock_config_manager.config.git.repository
    platform = mock_config_manager.config.git.host
    return platform, owner, repo_name, repo_url


@pytest.fixture
def mock_requests_response_factory():
    """
    Fixture to provide a reusable mock response factory for requests.get.
    
    This fixture returns a pre-configured mock object (`mock_requests_response`) that can be used to simulate HTTP responses from `requests.get` in tests. It is designed to avoid repetitive mock setup and ensure consistent mocking behavior across multiple test cases.
    
    Args:
        None.
    
    Returns:
        A mock object (`mock_requests_response`) that can be configured to return specific status codes, content, headers, or raise exceptions, allowing controlled testing of code that depends on `requests.get`.
    """
    return mock_requests_response


@pytest.fixture
def mock_repository_metadata(data_factory, repo_info):
    """
    Generates mock repository metadata using a data factory and repository information.
    
    Args:
        data_factory: An object responsible for generating repository metadata.
        repo_info: A tuple or list containing the platform, owner, repository name, and repository URL.
            The method unpacks this into four variables: platform, owner, repo_name, and repo_url.
    
    Returns:
        dict: The generated repository metadata.
    
    Why:
        This method serves as a wrapper that delegates the actual metadata generation to the provided data_factory.
        It unpacks the repo_info tuple/list to pass the individual components to the factory's method, ensuring the factory receives the necessary structured inputs.
    """
    platform, owner, repo_name, repo_url = repo_info
    return data_factory.generate_repository_metadata(platform, owner, repo_name, repo_url)


@pytest.fixture
def mock_api_raw_data(data_factory, repo_info):
    """
    Generates raw repository metadata using a data factory and repository information.
    
    Args:
        data_factory: An object responsible for generating mock repository metadata. It must have a `generate_repository_metadata_raw` method.
        repo_info: A tuple or list containing, in order: the platform (e.g., 'github'), the owner, the repository name, and the repository URL.
    
    Returns:
        dict: The raw repository metadata generated by the data factory.
    
    Why:
        This method provides a convenient wrapper to unpack the repository details from `repo_info` and pass them directly to the data factory's generation method. It simplifies the calling code by handling the unpacking step internally.
    """
    platform, owner, repo_name, repo_url = repo_info
    return data_factory.generate_repository_metadata_raw(platform, owner, repo_name, repo_url)


@pytest.fixture
def mock_parse_folder_name(mock_config_manager):
    """
    Mocks the parsing of a folder name from a repository URL.
    
    This method retrieves the repository URL from the provided mock configuration
    manager and delegates to the `parse_folder_name` helper to extract the
    corresponding folder name. It is used in testing to simulate the folder name
    extraction without performing actual Git operations.
    
    Args:
        mock_config_manager: The mock configuration manager object containing
            the Git repository configuration. Specifically, the repository URL
            is accessed via `mock_config_manager.config.git.repository`.
    
    Returns:
        The name of the folder where the repository would be cloned, as derived
        from the repository URL by the `parse_folder_name` helper.
    """
    repo_url = mock_config_manager.config.git.repository
    return parse_folder_name(repo_url)
