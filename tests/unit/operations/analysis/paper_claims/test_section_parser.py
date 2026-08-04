import json

import pytest

from osa_tool.operations.analysis.paper_claims.exceptions import SectionParsingError
from osa_tool.operations.analysis.paper_claims.section_parser import MarkdownSectionParser


def test_parse_preserves_heading_metadata_and_order():
    sections = MarkdownSectionParser().parse(
        "# 1. Introduction\r\nIntro text\r\n## 2.1 **Method**\r\nMethod text\r\n# Results\r\nResult text"
    )

    assert [item.section_id for item in sections] == ["s001", "s002", "s003"]
    assert [item.name for item in sections] == ["Introduction", "Method", "Results"]
    assert sections[1].heading_meta.numbering == "2.1"
    assert sections[1].heading_meta.level == 2
    assert sections[1].text == "Method text"


def test_parse_preserves_digits_in_unnumbered_headings():
    sections = MarkdownSectionParser().parse("# 3D Reconstruction\nBody\n# 2FA Authentication\nBody")

    assert [item.name for item in sections] == ["3D Reconstruction", "2FA Authentication"]
    assert [item.heading_meta.numbering for item in sections] == [None, None]


def test_write_json_preserves_section_ids(tmp_path):
    sections = MarkdownSectionParser().parse("# Method\nBody")
    output_path = MarkdownSectionParser.write_json(sections, tmp_path / "sections.json")

    assert json.loads(output_path.read_text(encoding="utf-8"))[0]["section_id"] == "s001"


@pytest.mark.parametrize("markdown", ["", "plain text without headings"])
def test_parse_rejects_markdown_without_sections(markdown):
    with pytest.raises(SectionParsingError):
        MarkdownSectionParser().parse(markdown)
