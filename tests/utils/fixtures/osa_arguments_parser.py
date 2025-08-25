from unittest.mock import patch, mock_open

import pytest

YAML_CONFIG_EXAMPLE = """
repository:
  type: str
  aliases: ["-r", "--repository"]
  description: "Git repository URL"
  default: "https://github.com/example/repo"

verbose:
  type: flag
  aliases: ["-v", "--verbose"]
  description: "Enable verbose output"
  default: false

timeout:
  type: int
  aliases: ["-t", "--timeout"]
  description: "Timeout in seconds"
  default: 30

platform_group:
  platform:
    type: str
    aliases: ["-p", "--platform"]
    description: "Target platform"
    choices: ["github", "gitlab", "gitverse"]
    default: "github"

  version:
    type: str
    aliases: ["--version"]
    description: "Platform version"
    default: "latest"

tags:
  type: list
  aliases: ["--tags"]
  description: "List of tags"
  default: []
"""


@pytest.fixture
def mock_yaml_file():
    with patch("builtins.open", mock_open(read_data=YAML_CONFIG_EXAMPLE)):
        yield


@pytest.fixture
def yaml_file_path():
    return "config/settings/arguments.yaml"
