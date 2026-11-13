import argparse
from unittest.mock import mock_open, patch

import pytest

from osa_tool.utils.arguments_parser import (
    build_parser_from_yaml,
    deep_merge_dicts,
    get_keys_from_group_in_yaml,
    read_arguments_file_flat,
    read_arguments_file,
    get_default_from_config,
)

MAIN_CLI_SECTIONS = ["settings", "arguments", "workflow"]


def _write_partial_config(tmp_path, content: str) -> str:
    config_file = tmp_path / "custom.toml"
    config_file.write_text(content, encoding="utf-8")
    return str(config_file)


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


def test_get_keys_from_group_in_yaml(mock_yaml_file):
    # Act
    keys = get_keys_from_group_in_yaml("platform_group")

    # Assert
    assert isinstance(keys, list)
    assert "platform" in keys
    assert "version" in keys


def test_get_keys_from_nonexistent_group(mock_yaml_file):
    # Act
    keys = get_keys_from_group_in_yaml("nonexistent_group")

    # Assert
    assert isinstance(keys, list)
    assert len(keys) == 0


def test_build_parser_from_yaml(mock_yaml_file, mock_toml_file):
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
    # Arrange
    parser = build_parser_from_yaml()

    # Act
    args = parser.parse_args(["-r", "https://github.com/test/repo", "-v", "-t", "60"])

    # Assert
    assert args.repository == "https://github.com/test/repo"
    assert args.verbose is True
    assert args.timeout == 60


def test_parser_default_values(mock_yaml_file, mock_toml_file):
    # Arrange
    parser = build_parser_from_yaml()

    # Act
    args = parser.parse_args([])

    # Assert
    assert args.repository == "https://github.com/example/repo"
    assert args.verbose is False
    assert args.timeout == 30


def test_parser_with_group_args(mock_yaml_file, mock_toml_file):
    # Arrange
    parser = build_parser_from_yaml()

    # Act
    args = parser.parse_args(["-p", "gitlab", "--version", "2.0"])

    # Assert
    assert args.platform == "gitlab"
    assert args.version == "2.0"


def test_parser_choices_validation(mock_yaml_file, mock_toml_file):
    # Arrange
    parser = build_parser_from_yaml()

    # Act
    args = parser.parse_args(["-p", "github"])

    # Assert
    assert args.platform == "github"
    with pytest.raises(SystemExit):
        parser.parse_args(["-p", "invalid_platform"])


def test_parser_list_type(mock_yaml_file, mock_toml_file):
    # Arrange
    parser = build_parser_from_yaml()

    # Act
    args = parser.parse_args(["--tags", "tag1", "tag2", "tag3"])

    # Assert
    assert isinstance(args.tags, list)
    assert args.tags == ["tag1", "tag2", "tag3"]


def test_parser_with_empty_list_default(mock_yaml_file, mock_toml_file):
    # Arrange
    parser = build_parser_from_yaml()

    # Act
    args = parser.parse_args([])

    # Assert
    assert isinstance(args.tags, list)
    assert args.tags == []


def test_parser_list_flag_without_values_returns_empty_list(mock_yaml_file, mock_toml_file):
    # Arrange
    parser = build_parser_from_yaml()

    # Act
    args = parser.parse_args(["--tags"])

    # Assert
    assert isinstance(args.tags, list)
    assert args.tags == []


def test_parser_rejects_empty_list_without_allow_empty(mock_yaml_file, mock_toml_file):
    parser = build_parser_from_yaml()

    with pytest.raises(SystemExit):
        parser.parse_args(["--required-tags"])


def test_get_default_from_config_returns_value(mock_toml_file):
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


def test_parser_tracks_explicit_cli_args(mock_yaml_file, mock_toml_file):
    parser = build_parser_from_yaml()

    args = parser.parse_args(["-r", "https://github.com/test/repo", "-v", "--tags", "tag1"])

    assert args._explicit_cli_args == {"repository", "verbose", "tags"}
    assert "timeout" not in args._explicit_cli_args
    assert args._cli_defaults["repository"] == "https://github.com/example/repo"
    assert args._cli_defaults["timeout"] == 30


def test_parser_choices_enforced(mock_yaml_file, mock_toml_file):
    # Arrange
    parser = build_parser_from_yaml()

    # Assert
    with pytest.raises(SystemExit):
        parser.parse_args(["-p", "invalid_platform"])


def test_real_settings_parser_accepts_host_api():
    parser = build_parser_from_yaml(extra_sections=["settings"])

    args = parser.parse_args(["--api", "host"])

    assert args.api == "host"
    with pytest.raises(SystemExit):
        parser.parse_args(["--api", "invalid"])


def test_unsupported_type_raises_error(mock_toml_file):
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


def test_deep_merge_dicts_merges_nested_and_replaces_lists():
    # Arrange
    base = {"general": {"mode": "auto", "translate_readme": []}, "llm": {"model": "a", "rate_limit": 10}}
    override = {"general": {"translate_readme": ["Russian"]}, "llm": {"model": "b"}}

    # Act
    merged = deep_merge_dicts(base, override)

    # Assert
    assert merged == {
        "general": {"mode": "auto", "translate_readme": ["Russian"]},
        "llm": {"model": "b", "rate_limit": 10},
    }
    assert base["general"]["translate_readme"] == []
    assert base["llm"]["model"] == "a"


@pytest.mark.parametrize("use_equals_form", [False, True])
def test_config_file_overrides_packaged_defaults(tmp_path, use_equals_form):
    # Arrange
    config_file = _write_partial_config(
        tmp_path, '[general]\ntranslate_readme = ["Russian"]\nartefacts_language = "Russian"\n'
    )
    config_args = [f"--config-file={config_file}"] if use_equals_form else ["--config-file", config_file]
    parser = build_parser_from_yaml(extra_sections=MAIN_CLI_SECTIONS)

    # Act
    args = parser.parse_args(["-r", "https://github.com/a/b", *config_args])

    # Assert
    assert args.translate_readme == ["Russian"]
    assert args.artefacts_language == "Russian"
    assert args._cli_defaults["artefacts_language"] == "Russian"
    assert "artefacts_language" not in args._explicit_cli_args


def test_explicit_cli_arg_beats_config_file(tmp_path):
    # Arrange
    config_file = _write_partial_config(tmp_path, '[general]\nartefacts_language = "Russian"\n')
    parser = build_parser_from_yaml(extra_sections=MAIN_CLI_SECTIONS)

    # Act
    args = parser.parse_args(["--config-file", config_file, "--artefacts-language", "German"])

    # Assert
    assert args.artefacts_language == "German"


def test_partial_config_file_keeps_packaged_defaults(tmp_path):
    # Arrange
    config_file = _write_partial_config(tmp_path, '[general]\nartefacts_language = "Russian"\n')
    parser = build_parser_from_yaml(extra_sections=MAIN_CLI_SECTIONS)
    packaged = parser.parse_args([])

    # Act
    args = parser.parse_args(["--config-file", config_file])

    # Assert
    assert args.mode == packaged.mode
    assert args.translate_readme == packaged.translate_readme
    assert args.model == packaged.model


def test_config_file_defaults_do_not_leak_between_parses(tmp_path):
    # Arrange
    config_file = _write_partial_config(tmp_path, '[general]\nartefacts_language = "Russian"\n')
    parser = build_parser_from_yaml(extra_sections=MAIN_CLI_SECTIONS)
    packaged_language = parser.parse_args([]).artefacts_language

    # Act
    parser.parse_args(["--config-file", config_file])
    args = parser.parse_args([])

    # Assert
    assert args.artefacts_language == packaged_language
    assert args._cli_defaults["artefacts_language"] == packaged_language


def test_missing_config_file_keeps_packaged_defaults(tmp_path):
    # Arrange
    parser = build_parser_from_yaml(extra_sections=MAIN_CLI_SECTIONS)
    packaged_language = parser.parse_args([]).artefacts_language

    # Act
    args = parser.parse_args(["--config-file", str(tmp_path / "missing.toml")])

    # Assert
    assert args.artefacts_language == packaged_language
