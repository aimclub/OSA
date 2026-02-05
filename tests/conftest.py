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
    return DataFactory()


# -------------------
# Config Manager Fixtures
# -------------------
@pytest.fixture
def mock_config_manager(data_factory, request):
    """Mock ConfigManager with dynamically generated test data"""
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
    """Fixture for tests that need to modify config"""

    def updater(**kwargs):
        for section, values in kwargs.items():
            if hasattr(mock_config_manager.config, section):
                if section == "llm":
                    current_llm = mock_config_manager.config.llm
                    if "default" in values:
                        default_dict = current_llm.default.dict()
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
    """Factory fixture to create SourceRank instances with patched methods."""

    def factory(repo_tree=None, method_overrides=None) -> SourceRank:
        overrides = method_overrides or {}
        random_methods = data_factory.random_source_rank_methods(force_overrides=overrides)

        patches = [
            patch("osa_tool.analytics.sourcerank.parse_folder_name", return_value=mock_parse_folder_name),
        ]

        if repo_tree is not None:
            patches.append(patch("osa_tool.analytics.sourcerank.get_repo_tree", return_value=repo_tree))

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
    return PromptLoader()


# -------------------
# RepositoryMetadata Fixtures
# -------------------
@pytest.fixture
def repo_info(mock_config_manager):
    full_name = mock_config_manager.config.git.full_name
    owner, repo_name = full_name.split("/")
    repo_url = mock_config_manager.config.git.repository
    platform = mock_config_manager.config.git.host
    return platform, owner, repo_name, repo_url


@pytest.fixture
def mock_requests_response_factory():
    """Fixture to provide a reusable mock response factory for requests.get."""
    return mock_requests_response


@pytest.fixture
def mock_repository_metadata(data_factory, repo_info):
    platform, owner, repo_name, repo_url = repo_info
    return data_factory.generate_repository_metadata(platform, owner, repo_name, repo_url)


@pytest.fixture
def mock_api_raw_data(data_factory, repo_info):
    platform, owner, repo_name, repo_url = repo_info
    return data_factory.generate_repository_metadata_raw(platform, owner, repo_name, repo_url)


@pytest.fixture
def mock_parse_folder_name(mock_config_manager):
    repo_url = mock_config_manager.config.git.repository
    return parse_folder_name(repo_url)
