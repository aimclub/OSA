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
    """
    Test that `load_configuration` correctly populates configuration fields from
    provided arguments.
    
    Parameters
    ----------
    mock_config_loader : MagicMock
        Mocked ConfigLoader used to provide a mock configuration object.
    mock_project_root : str
        Mocked project root path returned by the `osa_project_root` patch.
    repo_url : str
        Repository URL to be passed to `load_configuration`.
    api : str
        LLM API name to be passed to `load_configuration`.
    api_url : str
        Base URL for the LLM API.
    model : str
        Model name to be passed to `load_configuration`.
    expected_repo : str
        Expected repository URL in the resulting configuration.
    expected_api : str
        Expected LLM API name in the resulting configuration.
    expected_url : str
        Expected LLM API URL in the resulting configuration.
    expected_model : str
        Expected LLM model name in the resulting configuration.
    
    Returns
    -------
    None
        The function performs assertions and does not return a value.
    """
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
