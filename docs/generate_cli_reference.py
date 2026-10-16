"""Generate the normal OSA CLI reference tables from arguments.yaml."""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ARGUMENTS_PATH = ROOT / "osa_tool" / "config" / "settings" / "arguments.yaml"
REFERENCE_SECTIONS = {
    "arguments": "Task options",
    "settings": "Repository and model settings",
    "workflow": "Workflow options",
    "paper_analysis_cli": "Paper-analysis options",
}
TARGETS = {
    ROOT / "docs" / "scheduler" / "index.md": ("normal-cli-options", tuple(REFERENCE_SECTIONS)),
    ROOT / "docs" / "paper-analysis" / "index.md": ("paper-analysis-options", ("paper_analysis_cli",)),
}


def _markdown_cell(value: object) -> str:
    if value is None or value == []:
        return "—"
    lines = [line.strip() for line in str(value).strip().splitlines() if line.strip()]
    return "<br>".join(lines).replace("|", r"\|") or "—"


def _render_section(name: str, options: dict) -> str:
    rows = [
        "| Parameter | CLI options | Type | Required | Description | Choices |",
        "|:--|:--|:--|:--:|:--|:--|",
    ]
    for key, metadata in sorted(options.items()):
        if not isinstance(metadata, dict) or "aliases" not in metadata:
            continue
        aliases = "<br>".join(f"`{alias}`" for alias in metadata["aliases"])
        arg_type = _markdown_cell(metadata.get("type", "str"))
        required = "yes" if metadata.get("required", False) else "—"
        description = _markdown_cell(metadata.get("description", ""))
        choices = ", ".join(f"`{choice}`" for choice in metadata.get("choices", [])) or "—"
        rows.append(f"| `{key}` | {aliases} | {arg_type} | {required} | {description} | {choices} |")
    return f"### {name}\n\n" + "\n".join(rows)


def render_reference(source: dict, section_names: tuple[str, ...]) -> str:
    rendered = []
    for section_name in section_names:
        options = source.get(section_name, {})
        if not isinstance(options, dict):
            continue
        if options.get("metadata_only"):
            options = {key: value for key, value in options.items() if key != "metadata_only"}
        title = REFERENCE_SECTIONS.get(section_name, section_name.replace("_", " ").title())
        rendered.append(_render_section(title, options))
    return "\n\n".join(rendered)


def update_reference(path: Path, block_name: str, section_names: tuple[str, ...], source: dict, check: bool) -> bool:
    begin = f"<!-- BEGIN GENERATED: {block_name} -->"
    end = f"<!-- END GENERATED: {block_name} -->"
    document = path.read_text(encoding="utf-8")
    if begin not in document or end not in document:
        raise ValueError(f"Missing generated reference markers in {path}")
    before, remainder = document.split(begin, 1)
    _, after = remainder.split(end, 1)
    generated = render_reference(source, section_names)
    updated = f"{before}{begin}\n\n{generated}\n\n{end}{after}"
    if updated == document:
        return False
    if check:
        return True
    path.write_text(updated, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Report stale generated references without modifying documentation.",
    )
    args = parser.parse_args()

    source = yaml.safe_load(ARGUMENTS_PATH.read_text(encoding="utf-8"))
    stale = []
    for path, (block_name, sections) in TARGETS.items():
        changed = update_reference(path, block_name, sections, source, check=args.check)
        if changed:
            stale.append(path.relative_to(ROOT))

    if args.check:
        if stale:
            print("Generated CLI references are out of date:")
            for path in stale:
                print(f"  {path}")
            print("Run: python docs/generate_cli_reference.py")
            return 1
        print("Generated CLI references are up to date.")
        return 0

    for path in stale:
        print(f"Updated {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
