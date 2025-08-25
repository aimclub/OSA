import argparse
from unittest.mock import mock_open, patch

import pytest

from osa_tool.arguments_parser import (
    build_parser_from_yaml,
    get_keys_from_group_in_yaml,
    read_arguments_file_flat,
    read_arguments_file,
)


def test_read_arguments_file(mock_yaml_file, yaml_file_path):
    # Act
    data = read_arguments_file(yaml_file_path)

    # Assert
    assert isinstance(data, dict)
    assert "repository" in data
    assert "verbose" in data
    assert "timeout" in data
    assert "platform_group" in data


def test_read_arguments_file_flat(mock_yaml_file, yaml_file_path):
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


def test_get_keys_from_group_in_yaml(mock_yaml_file, yaml_file_path):
    # Act
    keys = get_keys_from_group_in_yaml(yaml_file_path, "platform_group")

    # Assert
    assert isinstance(keys, list)
    assert "platform" in keys
    assert "version" in keys


def test_get_keys_from_nonexistent_group(mock_yaml_file, yaml_file_path):
    # Act
    keys = get_keys_from_group_in_yaml(yaml_file_path, "nonexistent_group")

    # Assert
    assert isinstance(keys, list)
    assert len(keys) == 0


def test_build_parser_from_yaml(mock_yaml_file, yaml_file_path):
    # Act
    parser = build_parser_from_yaml(yaml_file_path)

    # Assert
    assert isinstance(parser, argparse.ArgumentParser)

    parser_help = parser.format_help()
    assert "-r" in parser_help
    assert "--repo" in parser_help
    assert "-v" in parser_help
    assert "--verbose" in parser_help
    assert "-t" in parser_help
    assert "--timeout" in parser_help


def test_parser_parsing_args(mock_yaml_file, yaml_file_path):
    # Arrange
    parser = build_parser_from_yaml(yaml_file_path)

    # Act
    args = parser.parse_args(["-r", "https://github.com/test/repo", "-v", "-t", "60"])

    # Assert
    assert args.repository == "https://github.com/test/repo"
    assert args.verbose is True
    assert args.timeout == 60


def test_parser_default_values(mock_yaml_file, yaml_file_path):
    # Arrange
    parser = build_parser_from_yaml(yaml_file_path)

    # Act
    args = parser.parse_args([])

    # Assert
    assert args.repository == "https://github.com/example/repo"
    assert args.verbose is False
    assert args.timeout == 30


def test_parser_with_group_args(mock_yaml_file, yaml_file_path):
    # Arrange
    parser = build_parser_from_yaml(yaml_file_path)

    # Act
    args = parser.parse_args(["-p", "gitlab", "--version", "2.0"])

    # Assert
    assert args.platform == "gitlab"
    assert args.version == "2.0"


def test_parser_choices_validation(mock_yaml_file, yaml_file_path):
    # Arrange
    parser = build_parser_from_yaml(yaml_file_path)

    # Act
    args = parser.parse_args(["-p", "github"])

    # Assert
    assert args.platform == "github"
    with pytest.raises(SystemExit):
        parser.parse_args(["-p", "invalid_platform"])


def test_parser_list_type(mock_yaml_file, yaml_file_path):
    # Arrange
    parser = build_parser_from_yaml(yaml_file_path)

    # Act
    args = parser.parse_args(["--tags", "tag1", "tag2", "tag3"])

    # Assert
    assert isinstance(args.tags, list)
    assert args.tags == ["tag1", "tag2", "tag3"]


def test_parser_with_empty_list_default(mock_yaml_file, yaml_file_path):
    # Arrange
    parser = build_parser_from_yaml(yaml_file_path)

    # Act
    args = parser.parse_args([])

    # Assert
    assert isinstance(args.tags, list)
    assert args.tags == []


def test_unsupported_type_raises_error():
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
            build_parser_from_yaml("invalid.yaml")
