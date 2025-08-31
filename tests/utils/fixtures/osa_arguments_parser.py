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
    with patch("builtins.open", mock_open(read_data=YAML_CONFIG_EXAMPLE)):
        yield


@pytest.fixture()
def mock_toml_file():
    with patch("osa_tool.arguments_parser.read_config_file", return_value=TOML_CONFIG_EXAMPLE):
        yield TOML_CONFIG_EXAMPLE


@pytest.fixture
def yaml_file_path():
    return "config/settings/arguments.yaml"
