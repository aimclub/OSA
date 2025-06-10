from unittest.mock import MagicMock, patch

import pytest

from osa_tool.run import load_configuration


@pytest.mark.parametrize(
    "repo_url, api, api_url, model, expected_repo, expected_api, expected_url, expected_model",
    [
        # First test case
        (
            "https://github.com/example/repo",
            "openai",
            "https://api.openai.com",
            "gpt-test",
            "https://github.com/example/repo",
            "openai",
            "https://api.openai.com",
            "gpt-test",
        ),
        # Second test case
        (
            "https://github.com/example2/repo2",
            "openai",
            "https://test-url.com",
            "gpt-test2",
            "https://github.com/example2/repo2",
            "openai",
            "https://test-url.com",
            "gpt-test2",
        ),
    ],
)
@patch("osa_tool.utils.osa_project_root", return_value="/mock/project/root")
@patch("osa_tool.config.settings.ConfigLoader", autospec=True)
def test_load_configuration(
    mock_config_loader,
    mock_project_root,
    repo_url,
    api,
    api_url,
    model,
    expected_repo,
    expected_api,
    expected_url,
    expected_model,
):
    # Arrange
    mock_config = MagicMock()
    mock_config_loader.return_value = mock_config

    # Act
    config = load_configuration(
        repo_url=repo_url,
        api=api,
        base_url=api_url,
        model_name=model,
    )

    # Assert
    assert config.config.git.repository == expected_repo
    assert config.config.llm.api == expected_api
    assert config.config.llm.url == expected_url
    assert config.config.llm.model == expected_model
