"""
Convert a PDF (bytes or path) to a list of {"name": str, "text": str} sections.

Uses pdfplumber (already in OSA requirements) instead of pymupdf.
Strategy mirrors VKR's original:
  1. Collect per-line text with max font size and bold flag.
  2. Identify headings as lines significantly larger than body text (or bold + short).
  3. Group body text between consecutive headings.
  4. Fallback to regex heuristic if fewer than 3 sections found.
"""
from __future__ import annotations

import io
import re
from collections import Counter
from typing import Optional


_HEADING_RE = re.compile(
    r"^(?:"
    r"\d+(?:\.\d+)*\.?\s+[A-Z][A-Za-z ,:\-]{2,60}"
    r"|(?:Abstract|Introduction|Background|Related\s+Work"
    r"|Literature\s+Review|Method(?:ology)?s?|Approach"
    r"|Experiments?(?:\s+Setup)?|Evaluation|Results?"
    r"|Discussion|Conclusion|Future\s+Work"
    r"|Acknowledgm(?:ent)?s?|References|Appendix)"
    r"[s]?[:\s]*"
    r")$",
    re.IGNORECASE | re.MULTILINE,
)


def _sections_from_regex(text: str) -> list[dict]:
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        return [{"name": "Document", "text": text.strip()}]
    sections: list[dict] = []
    for i, match in enumerate(matches):
        name = match.group().strip().rstrip(":")
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if name and body:
            sections.append({"name": name, "text": body})
    return sections


def _collect_line_spans(pdf_bytes: bytes) -> list[dict]:
    """
    Extract per-line text with font-size and bold info using pdfplumber characters.
    Returns list of {"text": str, "size": float, "bold": bool}.
    """
    import pdfplumber

    spans: list[dict] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as doc:
        for page in doc.pages:
            chars = page.chars
            if not chars:
                continue

            # Group characters into visual lines by their `top` coordinate.
            chars_sorted = sorted(chars, key=lambda c: (round(c["top"], 1), c["x0"]))
            current_top: Optional[float] = None
            line_chars: list[dict] = []

            def _flush(lchars: list[dict]) -> None:
                if not lchars:
                    return
                text = "".join(c.get("text", "") for c in lchars).strip()
                if not text:
                    return
                sizes = [c.get("size", 0) for c in lchars if c.get("size")]
                max_size = round(max(sizes), 1) if sizes else 0.0
                is_bold = any(
                    "bold" in (c.get("fontname") or "").lower() for c in lchars
                )
                spans.append({"text": text, "size": max_size, "bold": is_bold})

            for char in chars_sorted:
                top = round(char["top"], 1)
                if current_top is None:
                    current_top = top
                if abs(top - current_top) > 3:
                    _flush(line_chars)
                    line_chars = [char]
                    current_top = top
                else:
                    line_chars.append(char)
            _flush(line_chars)

    return spans


def _sections_from_pdfplumber(pdf_bytes: bytes) -> list[dict]:
    spans = _collect_line_spans(pdf_bytes)
    if not spans:
        return []

    sizes = [s["size"] for s in spans if s["size"] > 0]
    if not sizes:
        return []

    size_counts = Counter(round(s, 1) for s in sizes)
    body_size: float = size_counts.most_common(1)[0][0]
    heading_threshold = body_size * 1.12

    def _is_heading(span: dict) -> bool:
        text = span["text"]
        if len(text) > 120:
            return False
        if span["size"] >= heading_threshold:
            return True
        if span["bold"] and len(text) <= 80 and not text.endswith(","):
            return True
        return False

    sections: list[dict] = []
    current_name: Optional[str] = None
    current_lines: list[str] = []

    for span in spans:
        if _is_heading(span):
            if current_name and current_lines:
                sections.append(
                    {"name": current_name, "text": " ".join(current_lines).strip()}
                )
            current_name = span["text"].strip().rstrip(":")
            current_lines = []
        else:
            if current_name is not None:
                current_lines.append(span["text"])

    if current_name and current_lines:
        sections.append({"name": current_name, "text": " ".join(current_lines).strip()})

    return [s for s in sections if s["text"]]


def _plain_text(pdf_bytes: bytes) -> str:
    import pdfplumber

    pages_text: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as doc:
        for page in doc.pages:
            text = page.extract_text() or ""
            if text.strip():
                pages_text.append(text)
    return "\n".join(pages_text)


def parse_pdf_to_sections(pdf_bytes: bytes) -> list[dict]:
    """
    Parse a PDF (raw bytes) into a list of {"name": str, "text": str}.
    Returns at least one section even if structure detection fails.
    """
    sections = _sections_from_pdfplumber(pdf_bytes)

    if len(sections) < 3:
        plain = _plain_text(pdf_bytes)
        regex_sections = _sections_from_regex(plain)
        if len(regex_sections) >= len(sections):
            sections = regex_sections

    return sections if sections else [{"name": "Document", "text": "(no text extracted)"}]
