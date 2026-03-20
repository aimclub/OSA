from unittest.mock import patch, mock_open

import pytest

YAML_CONFIG_EXAMPLE = """
repository:
  type: str
  aliases: ["-r", "--repository"]
  description: "Git repository URL"

verbose:
  type: flag
  aliases: ["-v", "--verbose"]
  description: "Enable verbose output"

timeout:
  type: int
  aliases: ["-t", "--timeout"]
  description: "Timeout in seconds"

platform_group:
  platform:
    type: str
    aliases: ["-p", "--platform"]
    description: "Target platform"
    choices: ["github", "gitlab", "gitverse"]

  version:
    type: str
    aliases: ["--version"]
    description: "Platform version"

tags:
  type: list
  aliases: ["--tags"]
  description: "List of tags"
"""

TOML_CONFIG_EXAMPLE = {
    "git": {
        "repository": "https://github.com/example/repo",
    },
    "general": {
        "verbose": False,
        "timeout": 30,
        "platform": "github",
        "version": "latest",
        "tags": [],
    },
}


@pytest.fixture
def mock_yaml_file():
    """
    Mocks a YAML file using a predefined example configuration.
    
    This method uses a context manager to patch the built-in open function,
    simulating the presence of a YAML file with the content defined in
    YAML_CONFIG_EXAMPLE. It is designed to be used as a context manager
    or a pytest fixture, allowing tests to run without requiring an actual YAML file.
    
    Why:
    - To isolate unit tests from file system dependencies, ensuring tests are fast and reliable.
    - To provide a consistent, controlled YAML content for testing configuration parsing and handling.
    
    Yields:
        None: This method yields control to the caller while the patch is active.
        The patch remains in effect throughout the yielded block, after which it is automatically reverted.
    """
    with patch("builtins.open", mock_open(read_data=YAML_CONFIG_EXAMPLE)):
        yield


@pytest.fixture()
def mock_toml_file():
    """
    Mocks a TOML configuration file for testing purposes.
    
    This method uses a patch to intercept calls to the configuration file reader,
    ensuring that a predefined example configuration is returned instead of
    reading from the filesystem. It is designed to be used as a pytest fixture.
    This allows tests to run with a consistent, controlled configuration without
    dependencies on external files, improving test isolation and reliability.
    
    Args:
        None
    
    Yields:
        dict: A dictionary representing the parsed example TOML configuration.
    """
    with patch("osa_tool.utils.arguments_parser.read_config_file", return_value=TOML_CONFIG_EXAMPLE):
        yield TOML_CONFIG_EXAMPLE


@pytest.fixture
def yaml_file_path():
    """
    Provides the file path to the YAML configuration file used for tool arguments.
    
    This method returns a static relative path to the arguments configuration file, which contains settings and parameters for the OSA Tool's operations. The path is fixed because the tool expects the configuration file to be consistently located in the same directory structure for reliable access during execution.
    
    Returns:
        The relative path to the arguments YAML file as a string.
    """
    return "config/settings/arguments.yaml"
