from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from markdown_it import MarkdownIt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Prepare sections JSON from markdown produced by marker-pdf.")
    parser.add_argument("markdown", type=Path, help="Path to input markdown file")
    parser.add_argument("--output", type=Path, default=None, help="Optional output path for sections JSON")
    return parser


def validate_input(markdown_path: Path) -> None:
    if not markdown_path.exists():
        raise FileNotFoundError(f"Markdown not found: {markdown_path}")
    if not markdown_path.is_file():
        raise ValueError(f"Not a file: {markdown_path}")
    if markdown_path.suffix.lower() != ".md":
        raise ValueError(f"Expected a .md file, got: {markdown_path.name}")


def normalize_markdown(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").strip() + "\n"


def extract_sections_from_markdown(markdown_text: str) -> list[dict[str, object]]:
    md = MarkdownIt()
    tokens = md.parse(markdown_text)
    lines = markdown_text.splitlines()

    headings: list[tuple[int, int, str]] = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.type == "heading_open" and token.tag.startswith("h"):
            level = int(token.tag[1:])
            token_map = token.map or [0, 0]
            start_line = token_map[0]

            name = ""
            if i + 1 < len(tokens) and tokens[i + 1].type == "inline":
                name = tokens[i + 1].content.strip()

            if name:
                headings.append((start_line, level, name))
        i += 1

    sections: list[dict[str, object]] = []
    for idx, (start_line, level, name) in enumerate(headings):
        next_start = headings[idx + 1][0] if idx + 1 < len(headings) else len(lines)
        section_lines = lines[start_line + 1 : next_start]
        section_text = "\n".join(section_lines).strip()
        sections.append({"name": name, "text": section_text, "level": level})

    return sections


def clean_headings(data: list[dict[str, object]]) -> list[dict[str, object]]:
    cleaned = []
    for item in data:
        raw_name = str(item.get("name", "")).strip()
        level = int(item.get("level", 1))

        name = re.sub(r"[*_#`~]", "", raw_name)
        numbering_match = re.match(r"^\s*(\d+(?:\.\d+)*)\s*[\.)]?\s+", name)
        numbering = numbering_match.group(1) if numbering_match else None
        name = re.sub(r"^\s*\d+(?:\.\d+)*\s*[\.)]?\s*", "", name)
        name = re.sub(r"\s+", " ", name).strip()

        cleaned.append(
            {
                "name": name,
                "text": item.get("text", ""),
                "heading_meta": {"raw": raw_name, "level": level, "numbering": numbering},
            }
        )

    return cleaned


def write_sections_json(markdown_path: Path, sections: list[dict[str, object]], output_path: Path | None) -> Path:
    out_path = output_path if output_path else markdown_path.with_name(f"{markdown_path.stem}_sections_v3.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(sections, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        markdown_path = args.markdown.expanduser().resolve()
        output_path = args.output.expanduser().resolve() if args.output else None

        validate_input(markdown_path)
        markdown_text = normalize_markdown(markdown_path.read_text(encoding="utf-8"))
        sections = extract_sections_from_markdown(markdown_text)
        postprocessed_sections = clean_headings(sections)
        sections_json_path = write_sections_json(markdown_path, postprocessed_sections, output_path)
        print(f"Extracted {len(postprocessed_sections)} sections to: {sections_json_path}")
        return 0

    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
