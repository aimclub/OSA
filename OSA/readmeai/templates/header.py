from typing import Any, ClassVar

from OSA.readmeai.config.constants import HeaderStyleOptions
from OSA.readmeai.templates.base import BaseTemplate


class HeaderTemplate(BaseTemplate):
    """
    Class variable for rendering the README.md header style.
    """

    HEADER_TEMPLATES: ClassVar[dict] = {
        HeaderStyleOptions.CLASSIC: """\
<p align="{align}"><h1 align="{align}">{repo_name}</h1></p>
<p align="{align}">\n\t{shields_icons}</p>
<p align="{align}">{badges_tech_stack_text}</p>
<p align="{align}">\n\t{badges_tech_stack}</p>
<br>
""",
    }

    def __init__(self, style: str = HeaderStyleOptions.CLASSIC) -> None:
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
        return HeaderTemplate.HEADER_TEMPLATES[HeaderStyleOptions(template)]
