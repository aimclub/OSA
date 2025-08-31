import argparse
from typing import Any

import tomli
import yaml

from osa_tool.utils import build_arguments_path, build_config_path


def build_parser_from_yaml() -> argparse.ArgumentParser:
    """
    Build an ArgumentParser based on a YAML configuration file.

    Returns:
        argparse.ArgumentParser: Configured argument parser.
    """

    config_yaml = read_arguments_file(build_arguments_path())
    config_toml = read_config_file(build_config_path())

    parser = argparse.ArgumentParser(
        description="Generated CLI parser from YAML configuration",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    def add_arguments(group, args_dict):
        for key, options in args_dict.items():
            aliases = options.get("aliases", [])
            arg_type = options.get("type", "str")
            description = options.get("description", "")
            choices = options.get("choices")
            default = get_default_from_config(config_toml, key)
            kwargs = {"help": description}

            if arg_type == "flag":
                kwargs["action"] = "store_true"
                kwargs["default"] = default
            elif arg_type == "str":
                kwargs["type"] = str
                kwargs["default"] = default
                if choices:
                    kwargs["choices"] = choices
            elif arg_type == "int":
                kwargs["type"] = int
                kwargs["default"] = default
            elif arg_type == "list":
                kwargs["nargs"] = "+"
                kwargs["type"] = str
                kwargs["default"] = default
            else:
                raise ValueError(f"Unsupported type '{arg_type}' for argument '{key}'")

            group.add_argument(*aliases, **kwargs)

    core_args = {k: v for k, v in config_yaml.items() if not isinstance(v, dict) or "type" in v}
    add_arguments(parser, core_args)

    for group_name, group_args in config_yaml.items():
        if isinstance(group_args, dict) and "type" not in group_args:
            arg_group = parser.add_argument_group(f"{group_name} arguments")
            add_arguments(arg_group, group_args)

    return parser


def get_keys_from_group_in_yaml(group_name: str) -> list:
    data = read_arguments_file(build_arguments_path())
    keys = []
    for key, params in data.items():
        if key == group_name:
            keys.extend(list(params.keys()))
    return keys


def read_arguments_file_flat(yaml_path: str) -> dict:
    """
    Read YAML arguments file and flatten nested groups into a single dict.
    """
    data = read_arguments_file(yaml_path)
    flat_data = {}

    for key, value in data.items():
        if isinstance(value, dict) and all(isinstance(v, dict) for v in value.values()):
            for subkey, subvalue in value.items():
                flat_data[subkey] = subvalue
        else:
            flat_data[key] = value

    return flat_data


def get_default_from_config(config: dict, key: str) -> Any:
    """
    Find default value for a key in config dict by searching all top-level sections.
    """
    for section, values in config.items():
        if isinstance(values, dict) and key in values:
            return values[key]
    return None


def read_arguments_file(yaml_path: str) -> dict:
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


def read_config_file(toml_path: str) -> dict[str, Any]:
    """Load TOML config as a nested dict."""
    with open(toml_path, "rb") as f:
        data = tomli.load(f)
    return {k.lower(): v for k, v in data.items()}
