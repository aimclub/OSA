"""Tests for PdfSectionParser — regex and structure logic, no real PDF needed."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from osa_tool.operations.analysis.vkr_scoring.pdf_parser import PdfSectionParser


# ── _sections_from_regex ──────────────────────────────────────────────────────


def test_sections_from_regex_finds_headings():
    text = (
        "Abstract\n"
        "This is the abstract text.\n\n"
        "Results\n"
        "Here are the results.\n"
    )
    parser = PdfSectionParser(b"")  # pdf_bytes not needed for this method
    sections = parser._sections_from_regex(text)
    names = [s["name"] for s in sections]
    assert "Abstract" in names
    assert "Results" in names
    assert all(s["text"] for s in sections)


def test_sections_from_regex_no_headings():
    text = "This is just plain text without any recognizable headings. More content here."
    parser = PdfSectionParser(b"")
    sections = parser._sections_from_regex(text)
    assert len(sections) == 1
    assert sections[0]["name"] == "Document"
    assert sections[0]["text"] == text.strip()


# ── parse — fallback on empty ─────────────────────────────────────────────────


def test_parse_returns_fallback_on_empty():
    """When pdfplumber returns no chars and plain text is empty, parse() returns fallback."""
    with patch("pdfplumber.open") as mock_open:
        mock_doc = MagicMock()
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=False)
        mock_page = MagicMock()
        mock_page.chars = []
        mock_page.extract_text.return_value = ""
        mock_doc.pages = [mock_page]
        mock_open.return_value = mock_doc

        parser = PdfSectionParser(b"%PDF-fake")
        result = parser.parse()

    assert len(result) >= 1
    assert result[0]["name"] == "Document"


# ── _plain_text ───────────────────────────────────────────────────────────────


def test_plain_text_uses_pdfplumber():
    with patch("pdfplumber.open") as mock_open:
        mock_doc = MagicMock()
        mock_doc.__enter__ = MagicMock(return_value=mock_doc)
        mock_doc.__exit__ = MagicMock(return_value=False)
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "hello world"
        mock_doc.pages = [mock_page]
        mock_open.return_value = mock_doc

        parser = PdfSectionParser(b"%PDF-fake")
        text = parser._plain_text()

    assert "hello" in text
