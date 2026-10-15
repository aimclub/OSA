from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

from osa_tool.operations.analysis.paper_claims.section_parser import MarkdownSectionParser

REPO_ROOT = Path(__file__).resolve().parents[4]
COMPARISON_SCRIPT = REPO_ROOT / "parser-comparison" / "compare.py"
SPEC = importlib.util.spec_from_file_location("osa_parser_comparison", COMPARISON_SCRIPT)
assert SPEC is not None and SPEC.loader is not None
comparison = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = comparison
SPEC.loader.exec_module(comparison)


def test_cleanup_removes_parser_bookkeeping_and_page_number_lines_only():
    source = (
        '<file name="thesis__p0046-0050.pdf">\n'
        "\n45\n"
        "# Introduction\n"
        "The result was 45 percent.\n"
        "<!-- chunk:1-5 source:sheet.md -->\n"
        "ordinary body text\n"
    )

    cleaned = comparison.clean_markdown(source)

    assert cleaned == "\n# Introduction\nThe result was 45 percent.\nordinary body text\n"
    sections = MarkdownSectionParser().parse(cleaned)
    assert [section.name for section in sections] == ["Introduction"]
    assert "The result was 45 percent." in sections[0].text
    assert "ordinary body text" in sections[0].text


def test_section_matching_handles_normalized_duplicates_missing_and_reordered_headings():
    parser = MarkdownSectionParser()
    mistral = parser.parse(
        "# 1. Alpha\nMistral alpha body.\n"
        "# Shared\nFirst shared body.\n"
        "# Shared\nSecond shared body.\n"
        "# Mistral only\nUnmatched body.\n"
        "# Tail\nTail body.\n"
    )
    marker = parser.parse(
        "## 9. alpha\nMarker alpha body.\n"
        "## Shared\nFirst shared body.\n"
        "## Tail\nTail body.\n"
        "## Shared\nSecond shared body.\n"
        "## Marker only\nUnmatched body.\n"
    )

    result = comparison._document_result("thesis_test", mistral, marker)

    assert result["exact_count"] == 3
    assert result["normalized_count"] == 4
    assert result["exact_order_count"] == 2
    assert result["normalized_order_count"] == 3
    assert result["unmatched_mistral"] == ["Mistral only"]
    assert result["unmatched_marker"] == ["Marker only"]
    assert result["numbering_diffs"] == 1
    assert result["level_diffs"] == 4

    rows = {row["mistral_section_name"]: row for row in result["rows"] if row["mistral_section_name"] == "Alpha"}
    assert rows["Alpha"]["match_type"] == "normalized_only_match"
    assert rows["Alpha"]["wer"] == ""

    shared_rows = [row for row in result["rows"] if row["mistral_section_name"] == "Shared"]
    assert len(shared_rows) == 2
    assert all(row["match_type"] == "exact_match" for row in shared_rows)
    assert sum(row["exact_order_preserved"] for row in shared_rows) == result["exact_order_count"]
    assert all(row["wer"] != "" for row in shared_rows)


def test_title_normalization_is_case_insensitive_and_collapses_whitespace():
    assert comparison.normalize_title("  Early   Results ") == "early results"


def test_visible_text_scores_table_contents_without_markdown_delimiters():
    table_markdown = "| Name | Value |\n|---|---|\n| first<br>row | 42 |\n"
    plain_text = "Name Value\nfirst row 42"

    counts = comparison._error_counts(table_markdown, plain_text)

    assert counts.word_edits == 0
    assert counts.char_edits == 0
