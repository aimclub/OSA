import re
from typing import Any, ClassVar

from readmegen.config.constants import TocStyleOptions
from readmegen.templates.base import BaseTemplate


class TocTemplate(BaseTemplate):
    """
    Class variable for rendering the README.md Table of Contents.
    """

    TOC_TEMPLATES: ClassVar[dict] = {
        TocStyleOptions.BULLET: """## Table of Contents\n\n{toc_items}\n---\n""",
    }

    TOC_ITEM_TEMPLATES: ClassVar[dict[TocStyleOptions, str]] = {
        TocStyleOptions.BULLET: "- [{title}](#{anchor})\n",
    }

    def __init__(self, style: str = TocStyleOptions.BULLET.value) -> None:
        self.style = TocStyleOptions(style)

    @staticmethod
    def generate_anchor(title: str) -> str:
        """Generate an anchor link from the given title.
        # #-table-of-contents
        """
        emoji_pattern = re.compile(
            "["
            "\U0001f600-\U0001f64f"  # emoticons
            "\U0001f300-\U0001f5ff"  # symbols & pictographs
            "\U0001f680-\U0001f6ff"  # transport & map symbols
            "\U0001f1e0-\U0001f1ff"  # flags (iOS)
            "\U00002702-\U000027b0"
            "\U000024c2-\U0001f251"
            "]+",
            flags=re.UNICODE,
        )
        title = emoji_pattern.sub("", title)
        return title.lower().replace(" ", "-")

    def _generate_toc_items(
        self,
        sections: list[dict[str, Any]],
        level: int = 0,
        parent_number: str = "",
    ) -> str:
        """Generate Table of Contents items recursively."""
        toc = ""
        for index, section in enumerate(sections, start=1):

            indent = "  " * level
            title = section["title"]
            anchor = self.generate_anchor(title)

            item = self.TOC_ITEM_TEMPLATES[self.style].format(
                title=title,
                anchor=anchor,
            )

            toc += f"{indent}{item}"

        return toc

    def render(self, data: dict[str, Any]) -> str:
        """Render Table of Contents based on the current style and data."""
        toc_items = self._generate_toc_items(data["sections"])
        template = self.TOC_TEMPLATES[self.style]
        return template.format(toc_items=toc_items)

    @staticmethod
    def get_toc_template(template: str) -> str:
        """Get the Table of Contents template for the given style."""
        return TocTemplate.TOC_TEMPLATES[TocStyleOptions(template)]
