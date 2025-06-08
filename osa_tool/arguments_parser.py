import argparse

import yaml


def build_parser_from_yaml(yaml_path: str) -> argparse.ArgumentParser:
    """
    Build an ArgumentParser based on a YAML configuration file.

    Args:
        yaml_path: Path to the YAML file defining CLI arguments.

    Returns:
        argparse.ArgumentParser: Configured argument parser.
    """

    config = read_arguments_file(yaml_path)

    parser = argparse.ArgumentParser(
        description="Generated CLI parser from YAML configuration",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    def add_arguments(group, args_dict):
        for key, options in args_dict.items():
            aliases = options.get("aliases", [])
            arg_type = options.get("type", "str")
            description = options.get("description", "")
            default = options.get("default")
            choices = options.get("choices")

            kwargs = {"help": description}

            if arg_type == "flag":
                kwargs["action"] = "store_true"
                if default is not None:
                    kwargs["default"] = default
            elif arg_type == "str":
                kwargs["type"] = str
                if default is not None:
                    kwargs["default"] = default
                if choices:
                    kwargs["choices"] = choices
            elif arg_type == "int":
                kwargs["type"] = int
                if default is not None:
                    kwargs["default"] = default
            elif arg_type == "list":
                kwargs["nargs"] = "+"
                kwargs["type"] = str
                if default is not None:
                    kwargs["default"] = default
            else:
                raise ValueError(f"Unsupported type '{arg_type}' for argument '{key}'")

            group.add_argument(*aliases, **kwargs)

    core_args = {k: v for k, v in config.items() if not isinstance(v, dict) or "type" in v}
    add_arguments(parser, core_args)

    for group_name, group_args in config.items():
        if isinstance(group_args, dict) and "type" not in group_args:
            arg_group = parser.add_argument_group(f"{group_name} arguments")
            add_arguments(arg_group, group_args)

    return parser


def get_keys_from_group_in_yaml(yaml_path, group_name) -> list:
    data = read_arguments_file(yaml_path)
    keys = []
    for key, params in data.items():
        if key == group_name:
            keys.extend(list(params.keys()))
    return keys


def read_arguments_file_flat(yaml_path) -> dict:
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


def read_arguments_file(yaml_path) -> dict:
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data
