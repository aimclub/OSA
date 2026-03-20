from pathlib import Path

VALID_TOML_CONTENT = """
[prompts]
description = "Description prompt"
topics = "Topics prompt"
analyze_urls = "Analyze URLs prompt"
"""

INVALID_TOML_CONTENT = """
[prompts]
description = "Description prompt"
# Missing 'topics' and 'analyze_urls'
"""


def create_temp_toml_file(tmp_path: Path, content: str) -> Path:
    """
    Creates a temporary TOML file within a specific directory structure.
    
    This method creates a nested directory path 'config/settings' under the provided base path, writes the specified content to a file named 'prompts_about_section.toml', and ensures the file is encoded in UTF-8. It is primarily used for setting up isolated configuration files during testing or temporary runtime scenarios, ensuring proper directory hierarchy and file encoding without altering the main project structure.
    
    Args:
        tmp_path: The base directory path where the configuration structure will be created.
        content: The string content to be written into the TOML file.
    
    Returns:
        Path: The full path to the newly created TOML file.
    """
    config_dir = tmp_path / "config" / "settings"
    config_dir.mkdir(parents=True, exist_ok=True)
    file_path = config_dir / "prompts_about_section.toml"
    file_path.write_text(content, encoding="utf-8")
    return file_path
