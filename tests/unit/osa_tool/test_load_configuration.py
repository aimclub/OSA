import pytest
from unittest.mock import patch, MagicMock

from osa_tool.run import load_configuration

@pytest.mark.parametrize(
    "repo_url, api, api_url, model, article, workflows_output_dir, generate_workflows, "
    "include_tests, include_black, include_pep8, include_autopep8, include_fix_pep8, "
    "include_pypi, python_versions, pep8_tool, use_poetry, branches, codecov_token, include_codecov, "
    "expected_repo, expected_api, expected_url, expected_model, "
    "expected_output_dir, expected_generate_workflows, expected_include_tests, "
    "expected_include_black, expected_include_pep8, expected_include_autopep8, "
    "expected_include_fix_pep8, expected_include_pypi, expected_python_versions, "
    "expected_pep8_tool, expected_use_poetry, expected_branches, expected_codecov_token, expected_include_codecov",
    [
        # First test case
        (
            "https://github.com/example/repo", "openai", "https://api.openai.com", "gpt-test", None,
            ".github/workflows", True, True, True, True, False, False, False,
            ["3.8", "3.9", "3.10"], "flake8", False, [], "false",
            "https://github.com/example/repo", "openai", "https://api.openai.com", "gpt-test",
            ".github/workflows", True, True, True, True, False, False, False,
            ["3.8", "3.9", "3.10"], "flake8", False, [], "false", "true"
        ),
        # Second test case
        (
            "https://github.com/example/repo", "openai", "https://api.openai.com", "gpt-test-article", "article.pdf",
            "custom/workflows", False, False, False, False, True, True, True,
            ["3.7", "3.11"], "pylint", True, ["main", "dev"], "abc123",
            "https://github.com/example/repo", "openai", "https://api.openai.com", "gpt-test-article",
            "custom/workflows", False, False, False, False, True, True, True,
            ["3.7", "3.11"], "pylint", True, ["main", "dev"], "abc123", "true"
        )
    ]
)
@patch("osa_tool.utils.osa_project_root", return_value="/mock/project/root")
@patch("osa_tool.readmeai.config.settings.ConfigLoader", autospec=True)
@patch("osa_tool.readmeai.readmegen_article.config.settings.ArticleConfigLoader", autospec=True)
def test_load_configuration(mock_article_loader, mock_config_loader, mock_project_root,
                            repo_url, api, api_url, model, article, workflows_output_dir, generate_workflows,
                            include_tests, include_black, include_pep8, include_autopep8, include_fix_pep8,
                            include_pypi, python_versions, pep8_tool, use_poetry, branches, codecov_token, include_codecov,
                            expected_repo, expected_api, expected_url, expected_model,
                            expected_output_dir, expected_generate_workflows, expected_include_tests,
                            expected_include_black, expected_include_pep8, expected_include_autopep8,
                            expected_include_fix_pep8, expected_include_pypi, expected_python_versions,
                            expected_pep8_tool, expected_use_poetry, expected_branches, expected_codecov_token, expected_include_codecov):
    # Arrange
    mock_config = MagicMock()
    mock_config_loader.return_value = mock_config
    mock_article_loader.return_value = mock_config
    
    # Act
    config = load_configuration(
        repo_url=repo_url,
        api=api,
        base_url=api_url,
        model_name=model,
        article=article,
        workflows_output_dir=workflows_output_dir,
        generate_workflows=generate_workflows,
        include_tests=include_tests,
        include_black=include_black,
        include_pep8=include_pep8,
        include_autopep8=include_autopep8,
        include_fix_pep8=include_fix_pep8,
        include_pypi=include_pypi,
        python_versions=python_versions,
        pep8_tool=pep8_tool,
        use_poetry=use_poetry,
        branches=branches,
        codecov_token=codecov_token,
        include_codecov=include_codecov
    )
    
    # Assert
    assert config.config.git.repository == expected_repo
    assert config.config.llm.api == expected_api
    assert config.config.llm.url == expected_url
    assert config.config.llm.model == expected_model
    
    # workflow assertions
    assert config.config.workflows.output_dir == expected_output_dir
    assert config.config.workflows.generate_workflows == expected_generate_workflows
    assert config.config.workflows.include_tests == expected_include_tests
    assert config.config.workflows.include_black == expected_include_black
    assert config.config.workflows.include_pep8 == expected_include_pep8
    assert config.config.workflows.include_autopep8 == expected_include_autopep8
    assert config.config.workflows.include_fix_pep8 == expected_include_fix_pep8
    assert config.config.workflows.include_pypi == expected_include_pypi
    assert config.config.workflows.python_versions == expected_python_versions
    assert config.config.workflows.pep8_tool == expected_pep8_tool
    assert config.config.workflows.use_poetry == expected_use_poetry
    assert config.config.workflows.branches == expected_branches
    assert config.config.workflows.codecov_token == expected_codecov_token
    assert config.config.workflows.codecov_token == expected_codecov_token
    assert config.config.workflows.include_codecov == expected_include_codecov