from __future__ import annotations

import json
import re
from pathlib import Path

from markdown_it import MarkdownIt

from osa_tool.operations.analysis.paper_claims.exceptions import SectionParsingError
from osa_tool.operations.analysis.paper_claims.models import HeadingMeta, PaperSection


class MarkdownSectionParser:
    @staticmethod
    def normalize(markdown: str) -> str:
        normalized = markdown.replace("\r\n", "\n").replace("\r", "\n").strip()
        return normalized + "\n" if normalized else ""

    def parse(self, markdown: str) -> list[PaperSection]:
        text = self.normalize(markdown)
        if not text:
            raise SectionParsingError("Marker produced empty Markdown")
        tokens = MarkdownIt().parse(text)
        lines = text.splitlines()
        headings: list[tuple[int, int, str]] = []
        for index, token in enumerate(tokens):
            if token.type != "heading_open" or not token.tag.startswith("h"):
                continue
            name = tokens[index + 1].content.strip() if index + 1 < len(tokens) else ""
            if name:
                headings.append(((token.map or [0, 0])[0], int(token.tag[1:]), name))
        if not headings:
            raise SectionParsingError("Marker Markdown contains no usable headings")

        sections: list[PaperSection] = []
        for index, (start, level, raw_name) in enumerate(headings, start=1):
            next_start = headings[index][0] if index < len(headings) else len(lines)
            section_text = "\n".join(lines[start + 1 : next_start]).strip()
            cleaned = re.sub(r"[*_#`~]", "", raw_name)
            match = re.match(r"^\s*(\d+(?:\.\d+)*)\s*[.)]?\s+", cleaned)
            numbering = match.group(1) if match else None
            cleaned = re.sub(r"^\s*\d+(?:\.\d+)*\s*[.)]?\s*", "", cleaned)
            cleaned = re.sub(r"\s+", " ", cleaned).strip()
            if not cleaned:
                continue
            sections.append(
                PaperSection(
                    section_id=f"s{len(sections) + 1:03d}",
                    name=cleaned,
                    text=section_text,
                    heading_meta=HeadingMeta(raw=raw_name, level=level, numbering=numbering),
                )
            )
        if not sections:
            raise SectionParsingError("Marker Markdown contains no usable sections")
        return sections

    @staticmethod
    def write_json(sections: list[PaperSection], output_path: Path) -> Path:
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [section.model_dump(mode="json", exclude={"section_id"}) for section in sections]
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path
