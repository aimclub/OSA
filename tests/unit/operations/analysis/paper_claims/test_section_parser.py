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


@pytest.mark.parametrize("markdown", ["", "plain text without headings"])
def test_parse_rejects_markdown_without_sections(markdown):
    with pytest.raises(SectionParsingError):
        MarkdownSectionParser().parse(markdown)
