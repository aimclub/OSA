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
    config_dir = tmp_path / "config" / "settings"
    config_dir.mkdir(parents=True, exist_ok=True)
    file_path = config_dir / "prompts_about_section.toml"
    file_path.write_text(content, encoding="utf-8")
    return file_path
