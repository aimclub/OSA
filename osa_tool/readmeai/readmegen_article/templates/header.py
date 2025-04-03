from typing import Any, ClassVar

from osa_tool.readmeai.config.constants import HeaderStyleOptions
from osa_tool.readmeai.templates.base import BaseTemplate


class ArticleHeaderTemplate(BaseTemplate):
    """
    Class variable for rendering the README.md header style.
    """

    HEADER_TEMPLATES: ClassVar[dict] = {
        HeaderStyleOptions.CLASSIC: """\
<p align="{align}"><h1 align="{align}">{repo_name}</h1></p>
<p align="center">
  <a href="https://itmo.ru/"><img src="https://raw.githubusercontent.com/aimclub/open-source-ops/43bb283758b43d75ec1df0a6bb4ae3eb20066323/badges/ITMO_badge.svg"></a>
  <a href="https://github.com/ITMO-NSS-team/Open-Source-Advisor"><img src="https://img.shields.io/badge/improved%20by-OSA-blue"></a>
</p>
""",
    }

    def __init__(self, style: HeaderStyleOptions = HeaderStyleOptions.CLASSIC) -> None:
        self.style = style

    def render(self, data: dict[str, Any]) -> str:
        """Render the header based on the provided data."""
        template = self.HEADER_TEMPLATES.get(
            self.style,
            self.HEADER_TEMPLATES[HeaderStyleOptions.CLASSIC],
        )
        return template.format(**data)

    @staticmethod
    def get_header_template(template: str) -> str:
        """Get the header template for the given style."""
        return ArticleHeaderTemplate.HEADER_TEMPLATES[HeaderStyleOptions(template)]
