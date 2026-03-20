import argparse
from typing import Any

import tomli
import yaml

from osa_tool.utils.utils import build_arguments_path, build_config_path


def build_parser_from_yaml(extra_sections: list[str] | None = None) -> argparse.ArgumentParser:
    """
    Build an ArgumentParser based on a YAML configuration file.
    
    The method loads argument definitions from a YAML file and default values from a TOML configuration file, then dynamically constructs a command-line argument parser. This allows the CLI to be generated from external configuration files, making it easy to add or modify arguments without changing the source code.
    
    Args:
        extra_sections: Optional list of section names from the YAML file to include. If provided, only the core arguments and the specified section groups are added to the parser. This is used to create specialized pipelines that expose only a subset of available arguments.
    
    Returns:
        Configured argument parser with core arguments and optionally selected argument groups. The parser uses RawTextHelpFormatter to preserve formatting in help text.
    
    Why:
        This approach decouples argument definitions from the Python code, enabling non-developers to adjust CLI options via configuration files. It also supports modular argument groups for different pipeline stages or use cases.
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
            elif arg_type == "float":
                kwargs["type"] = float
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
            if extra_sections and group_name not in extra_sections:
                continue
            arg_group = parser.add_argument_group(f"{group_name} arguments")
            add_arguments(arg_group, group_args)

    return parser


def get_keys_from_group_in_yaml(group_name: str) -> list:
    """
    Retrieves all parameter keys belonging to a specified group from the arguments YAML file.
    
    Args:
        group_name: The name of the group for which to retrieve parameter keys.
    
    Returns:
        list: A list of strings, each being a parameter key found within the specified group.
    
    Why:
        This method allows the caller to obtain all configuration parameter keys defined under a specific group in the arguments YAML file. It is useful for dynamically inspecting the available configuration options within a named group, supporting operations that require knowledge of the defined parameters.
    """
    data = read_arguments_file(build_arguments_path())
    keys = []
    for key, params in data.items():
        if key == group_name:
            keys.extend(list(params.keys()))
    return keys


def read_arguments_file_flat(yaml_path: str) -> dict:
    """
    Read YAML arguments file and flatten nested groups into a single dict.
    
    This method processes a YAML configuration file by flattening any nested groups
    that are dictionaries of dictionaries into a single top-level dictionary.
    It ensures that arguments are accessible directly without navigating through
    group hierarchies, simplifying downstream access to configuration values.
    
    Args:
        yaml_path: The file system path to the YAML file to be read.
    
    Returns:
        A dictionary where all configuration arguments are flattened to the top level.
        If a key in the original data maps to a dict whose values are all dicts,
        each of those sub-dictionaries is promoted to the top level using its subkey.
        Otherwise, key-value pairs are preserved as-is.
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
    
    This method iterates through each top-level section (key-value pair) in the provided config dictionary. If a section's value is itself a dictionary and contains the specified key, the corresponding value is returned. This allows for retrieving default configuration values that may be nested within different sections without requiring knowledge of which specific section holds the key.
    
    Args:
        config: The configuration dictionary to search within.
        key: The key for which to find a default value.
    
    Returns:
        The value associated with the key if found in any top-level section's dictionary; otherwise, None.
    """
    for section, values in config.items():
        if isinstance(values, dict) and key in values:
            return values[key]
    return None


def read_arguments_file(yaml_path: str) -> dict:
    """
    Reads and parses a YAML file containing configuration arguments.
    
    Args:
        yaml_path: The file system path to the YAML file to be read.
    
    Returns:
        dict: A dictionary containing the data loaded from the YAML file.
    
    Why:
        This method centralizes YAML file reading with safe loading to prevent arbitrary code execution, ensuring configuration arguments are securely and consistently loaded from a specified file path.
    """
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data


def read_config_file(toml_path: str) -> dict[str, Any]:
    """
    Load TOML configuration file and return its contents as a nested dictionary with normalized keys.
    
    The method reads a TOML file from the given path, parses it using `tomli`, and converts all top-level keys to lowercase. This normalization ensures consistent key access regardless of the original casing in the TOML file, which is useful for case-insensitive configuration handling.
    
    Args:
        toml_path: Path to the TOML configuration file to be loaded.
    
    Returns:
        A dictionary representing the TOML data, where all top-level keys are lowercase and the values preserve their original nested structure.
    """
    with open(toml_path, "rb") as f:
        data = tomli.load(f)
    return {k.lower(): v for k, v in data.items()}
