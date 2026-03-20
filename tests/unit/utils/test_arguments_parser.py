import argparse
from unittest.mock import mock_open, patch

import pytest

from osa_tool.utils.arguments_parser import (
    build_parser_from_yaml,
    get_keys_from_group_in_yaml,
    read_arguments_file_flat,
    read_arguments_file,
    get_default_from_config,
)


def test_read_arguments_file(mock_yaml_file, yaml_file_path):
    """
    Tests the read_arguments_file function with a mocked YAML file.
    
    Args:
        mock_yaml_file: A pytest fixture providing a mocked YAML file.
        yaml_file_path: The path to the YAML file to be read during the test.
    
    The test verifies that the returned data is a dictionary containing the
    expected keys: "repository", "verbose", "timeout", and "platform_group".
    It also confirms the data type is a dictionary. This ensures the helper function
    correctly loads and parses the YAML configuration into the expected structure.
    """
    # Act
    data = read_arguments_file(yaml_file_path)

    # Assert
    assert isinstance(data, dict)
    assert "repository" in data
    assert "verbose" in data
    assert "timeout" in data
    assert "platform_group" in data


def test_read_arguments_file_flat(mock_yaml_file, yaml_file_path):
    """
    Test the read_arguments_file_flat function with a flat YAML file.
    
    This test verifies that the function correctly reads a YAML file and returns
    a flat dictionary containing the expected top-level keys, while ensuring
    that nested group keys are not present. It ensures the flattening behavior
    works as intended by checking for the presence of direct configuration keys
    and the absence of a group key that would indicate nested structure.
    
    Args:
        mock_yaml_file: A mock object representing the YAML file, used to simulate file I/O.
        yaml_file_path: The file path to the YAML file being tested, passed to the function under test.
    
    Returns:
        None
    """
    # Act
    flat_data = read_arguments_file_flat(yaml_file_path)

    # Assert
    assert isinstance(flat_data, dict)
    assert "repository" in flat_data
    assert "verbose" in flat_data
    assert "timeout" in flat_data
    assert "platform" in flat_data
    assert "version" in flat_data
    assert "platform_group" not in flat_data


def test_get_keys_from_group_in_yaml(mock_yaml_file):
    """
    Tests the retrieval of parameter keys for a specific group from the YAML file.
    
    This test verifies that `get_keys_from_group_in_yaml` correctly returns a list of parameter keys defined under the specified group in the mocked YAML configuration. It ensures the returned keys match expected values, confirming the helper function's ability to extract group-specific configuration parameters.
    
    Args:
        mock_yaml_file: A pytest fixture mocking the YAML file to provide test data.
    
    Why:
        Validating key retrieval is essential to ensure that the tool can dynamically inspect and utilize configuration parameters organized by groups, which supports operations requiring knowledge of available settings within the OSA Tool's argument structure.
    """
    # Act
    keys = get_keys_from_group_in_yaml("platform_group")

    # Assert
    assert isinstance(keys, list)
    assert "platform" in keys
    assert "version" in keys


def test_get_keys_from_nonexistent_group(mock_yaml_file):
    """
    Tests retrieving keys from a nonexistent group in the YAML file.
    
    This test verifies that when a group name not present in the YAML file is queried,
    the helper function returns an empty list instead of raising an error or returning invalid data.
    
    Args:
        mock_yaml_file: A fixture providing a mock YAML file for testing.
    
    Why:
        Ensures the system gracefully handles requests for non‑existent configuration groups,
        which is important for robustness when dynamically inspecting available parameters.
    
    Returns:
        None
    """
    # Act
    keys = get_keys_from_group_in_yaml("nonexistent_group")

    # Assert
    assert isinstance(keys, list)
    assert len(keys) == 0


def test_build_parser_from_yaml(mock_yaml_file, mock_toml_file):
    """
    Tests the build_parser_from_yaml function.
    
    This test verifies that the function returns a properly configured argparse.ArgumentParser.
    It checks that the parser's help text contains specific expected command-line argument flags.
    
    Args:
        mock_yaml_file: A mock YAML configuration file fixture.
        mock_toml_file: A mock TOML configuration file fixture.
    
    Why:
        The test ensures that the parser, which is built dynamically from external configuration files, correctly includes the core command-line arguments defined in those files. This validates that the configuration-driven approach works as intended, allowing CLI arguments to be managed without modifying source code.
    
    Note:
        The test does not call the helper function with any arguments; it uses the default behavior to load the core argument definitions.
    """
    # Act
    parser = build_parser_from_yaml()

    # Assert
    assert isinstance(parser, argparse.ArgumentParser)

    parser_help = parser.format_help()
    assert "-r" in parser_help
    assert "--repo" in parser_help
    assert "-v" in parser_help
    assert "--verbose" in parser_help
    assert "-t" in parser_help
    assert "--timeout" in parser_help


def test_parser_parsing_args(mock_yaml_file, mock_toml_file):
    """
    Test that the argument parser correctly parses command-line arguments.
    
    This test verifies that the parser, built from a YAML configuration, properly interprets specific command-line inputs and assigns them to the expected argument attributes.
    
    Args:
        mock_yaml_file: Fixture providing a mock YAML configuration file.
        mock_toml_file: Fixture providing a mock TOML configuration file.
    
    Why:
        The test ensures that the dynamically generated parser from external configuration files functions correctly, confirming that core arguments like repository URL, verbosity flag, and timeout are parsed as intended. This validation is crucial because the CLI behavior depends on configuration files rather than hardcoded argument definitions.
    """
    # Arrange
    parser = build_parser_from_yaml()

    # Act
    args = parser.parse_args(["-r", "https://github.com/test/repo", "-v", "-t", "60"])

    # Assert
    assert args.repository == "https://github.com/test/repo"
    assert args.verbose is True
    assert args.timeout == 60


def test_parser_default_values(mock_yaml_file, mock_toml_file):
    """
    Tests that the argument parser uses default values when no command-line arguments are provided.
    
    This test verifies that when the parser is invoked with an empty argument list, the parsed arguments correctly reflect the default values defined in the configuration files. This ensures the CLI behaves predictably when no user overrides are supplied.
    
    Args:
        mock_yaml_file: Fixture providing a mock YAML configuration file.
        mock_toml_file: Fixture providing a mock TOML configuration file.
    
    Why:
        The test confirms that the parser's default loading mechanism works as intended, which is critical because the tool relies on external configuration files to define CLI behavior. Without correct defaults, the tool might fail or behave unexpectedly when launched without explicit arguments.
    """
    # Arrange
    parser = build_parser_from_yaml()

    # Act
    args = parser.parse_args([])

    # Assert
    assert args.repository == "https://github.com/example/repo"
    assert args.verbose is False
    assert args.timeout == 30


def test_parser_with_group_args(mock_yaml_file, mock_toml_file):
    """
    Tests the argument parser with group-specific arguments.
    
    This test verifies that the argument parser correctly handles command-line arguments
    when using a configuration that includes group-specific argument definitions.
    Specifically, it checks that arguments defined in specialized groups (such as those
    for a particular platform) are parsed accurately and assigned the expected values.
    
    Args:
        mock_yaml_file: Fixture providing a mock YAML configuration file.
        mock_toml_file: Fixture providing a mock TOML configuration file.
    
    Why:
        The test ensures that the parser, which is built dynamically from external
        configuration files, properly integrates group-specific arguments into the
        command-line interface. This validates that the decoupled configuration
        approach works correctly for specialized use cases, allowing different
        argument groups to be exposed without modifying the source code.
    """
    # Arrange
    parser = build_parser_from_yaml()

    # Act
    args = parser.parse_args(["-p", "gitlab", "--version", "2.0"])

    # Assert
    assert args.platform == "gitlab"
    assert args.version == "2.0"


def test_parser_choices_validation(mock_yaml_file, mock_toml_file):
    """
    Test the validation of choices in the argument parser.
    
    This test verifies that the argument parser correctly validates the 'platform'
    argument against allowed choices. It ensures that valid choices are accepted
    and invalid choices raise a SystemExit error.
    
    Args:
        mock_yaml_file: Fixture providing a mock YAML configuration file.
        mock_toml_file: Fixture providing a mock TOML configuration file.
    
    Why:
        The test uses fixtures to simulate configuration files, ensuring the parser
        is built with the same argument definitions as in production. This isolates
        the test from external file dependencies and focuses on the validation logic.
    
    Steps:
        1. Build a parser from the YAML configuration using `build_parser_from_yaml`.
        2. Parse a valid platform choice ("github") and verify it is accepted.
        3. Attempt to parse an invalid platform choice ("invalid_platform") and
           confirm that it raises SystemExit, indicating proper validation failure.
    """
    # Arrange
    parser = build_parser_from_yaml()

    # Act
    args = parser.parse_args(["-p", "github"])

    # Assert
    assert args.platform == "github"
    with pytest.raises(SystemExit):
        parser.parse_args(["-p", "invalid_platform"])


def test_parser_list_type(mock_yaml_file, mock_toml_file):
    """
    Tests that the parser correctly handles a list-type argument.
    
    Args:
        mock_yaml_file: A fixture providing a mock YAML configuration file.
        mock_toml_file: A fixture providing a mock TOML configuration file.
    
    The test verifies that when the argument parser is provided with multiple
    values for the '--tags' option, it correctly stores them as a list.
    This ensures the parser properly interprets and stores repeated command-line values as a list, which is essential for arguments that accept multiple inputs (like tags).
    The test uses a parser built from a YAML configuration to validate that the list-type behavior works as defined in the external configuration.
    """
    # Arrange
    parser = build_parser_from_yaml()

    # Act
    args = parser.parse_args(["--tags", "tag1", "tag2", "tag3"])

    # Assert
    assert isinstance(args.tags, list)
    assert args.tags == ["tag1", "tag2", "tag3"]


def test_parser_with_empty_list_default(mock_yaml_file, mock_toml_file):
    """
    Tests that the parser correctly handles an empty argument list with default list values.
    
    This test verifies that when the command-line argument parser is invoked with an empty list (simulating no arguments provided by the user), it properly initializes list-type arguments to an empty list as defined in the configuration. This ensures default list values are applied correctly and the parser does not raise errors or produce unexpected types.
    
    Args:
        mock_yaml_file: Fixture providing a mock YAML configuration file.
        mock_toml_file: Fixture providing a mock TOML configuration file.
    """
    # Arrange
    parser = build_parser_from_yaml()

    # Act
    args = parser.parse_args([])

    # Assert
    assert isinstance(args.tags, list)
    assert args.tags == []


def test_get_default_from_config_returns_value(mock_toml_file):
    """
    Tests that get_default_from_config returns the expected default values for various keys.
    
    This test verifies that the helper function correctly retrieves predefined default values from a mocked configuration structure for a set of specific keys. It ensures the configuration lookup behaves as intended across different data types (string, integer, boolean, list).
    
    Args:
        mock_toml_file: A mock configuration object (dictionary) used as the source for retrieving default values. It is expected to contain nested sections where the target keys reside.
    
    Returns:
        None
    """
    # Arrange
    config = mock_toml_file

    # Assert
    assert get_default_from_config(config, "repository") == "https://github.com/example/repo"
    assert get_default_from_config(config, "timeout") == 30
    assert get_default_from_config(config, "verbose") is False
    assert get_default_from_config(config, "platform") == "github"
    assert get_default_from_config(config, "version") == "latest"
    assert get_default_from_config(config, "tags") == []


def test_parser_uses_toml_defaults(mock_yaml_file, mock_toml_file):
    """
    Test that the parser uses TOML defaults when no command-line arguments are provided.
    
    This test method verifies that the argument parser, built from a YAML configuration,
    correctly falls back to default values defined in a TOML configuration file when
    the command line argument list is empty. The test ensures that the parser's behavior
    matches the expected defaults for key arguments when no overrides are supplied.
    
    Args:
        mock_yaml_file: A mock YAML configuration file fixture.
        mock_toml_file: A mock TOML configuration file fixture.
    
    Why:
        This test validates the integration between the YAML-based argument definitions and the TOML-based default values, confirming that the parser correctly sources defaults from the TOML file in the absence of command-line input. This is essential for ensuring the CLI behaves predictably when users do not provide explicit arguments.
    """
    # Arrange
    parser = build_parser_from_yaml()

    # Act
    args = parser.parse_args([])

    # Assert
    assert args.repository == "https://github.com/example/repo"
    assert args.timeout == 30
    assert args.verbose is False
    assert args.platform == "github"
    assert args.version == "latest"
    assert args.tags == []


def test_parser_overrides_toml_defaults(mock_yaml_file, mock_toml_file):
    """
    Tests that command-line arguments override default values loaded from TOML configuration.
    
    This test ensures that when arguments are provided via the command line, they take precedence over the default values defined in the TOML configuration file. This is a key behavior for allowing users to customize tool execution at runtime without modifying configuration files.
    
    Args:
        mock_yaml_file: Fixture providing a mock YAML configuration file used to define the argument parser structure.
        mock_toml_file: Fixture providing a mock TOML configuration file used to supply default argument values.
    
    Why:
        Validating that command-line overrides work correctly is essential for the tool's usability, as it confirms that runtime user inputs properly supersede static configuration defaults, ensuring flexible and dynamic operation.
    """
    # Arrange
    parser = build_parser_from_yaml()

    # Act
    args = parser.parse_args(
        [
            "-r",
            "https://github.com/test/repo",
            "-v",
            "-t",
            "60",
            "-p",
            "gitlab",
            "--version",
            "2.0",
            "--tags",
            "tag1",
            "tag2",
        ]
    )

    # Assert
    assert args.repository == "https://github.com/test/repo"
    assert args.verbose is True
    assert args.timeout == 60
    assert args.platform == "gitlab"
    assert args.version == "2.0"
    assert args.tags == ["tag1", "tag2"]


def test_parser_choices_enforced(mock_yaml_file, mock_toml_file):
    """
    Tests that the parser enforces valid choices for the platform argument.
    
    This test verifies that the argument parser, built from external configuration files, correctly rejects invalid values for the platform argument. It ensures the CLI only accepts predefined choices, maintaining consistency and preventing runtime errors from unsupported platforms.
    
    Args:
        mock_yaml_file: Fixture providing a mock YAML configuration file.
        mock_toml_file: Fixture providing a mock TOML configuration file.
    
    Raises:
        SystemExit: When an invalid platform value is provided, confirming the parser enforces the allowed choices.
    """
    # Arrange
    parser = build_parser_from_yaml()

    # Assert
    with pytest.raises(SystemExit):
        parser.parse_args(["-p", "invalid_platform"])


def test_unsupported_type_raises_error(mock_toml_file):
    """
    Test that an unsupported type in the YAML configuration raises a ValueError.
    
    This test verifies that when the YAML configuration file defines an argument with a type that is not supported by the parser, the `build_parser_from_yaml` function raises a ValueError with a specific error message. This ensures that invalid configurations are caught early and provide clear feedback.
    
    Args:
        mock_toml_file: A mock file object used to simulate reading a TOML file. The TOML file is expected to contain default values, but this test focuses on the YAML validation.
    
    Why:
        The test uses a mock YAML string containing an unsupported type to isolate the validation behavior. By patching `builtins.open` to return this invalid YAML content, it confirms that the parser correctly rejects unsupported types, maintaining the integrity of the CLI configuration.
    """
    # Arrange
    invalid_yaml = """
invalid_arg:
  type: "unsupported_type"
  aliases: ["--invalid"]
  description: "Invalid argument type"
"""

    # Assert
    with patch("builtins.open", mock_open(read_data=invalid_yaml)):
        with pytest.raises(ValueError, match="Unsupported type 'unsupported_type'"):
            build_parser_from_yaml()
