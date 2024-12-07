from pathlib import Path

from readmegen.config.settings import BadgeStyleOptions, ConfigLoader
from readmegen.generators import badges
from readmegen.ingestion.models import RepositoryContext
from readmegen.readers.git.providers import GitHost
from readmegen.templates.header import HeaderTemplate
from readmegen.templates.quickstart import QuickStartBuilder


class MarkdownBuilder:
    """
    Builds each section of the README Markdown file.
    """

    def __init__(
        self,
        config_loader: ConfigLoader,
        repo_context: RepositoryContext,
        temp_dir: str,
    ):
        self.config_loader = config_loader
        self.config = config_loader.config
        self.deps = repo_context.dependencies
        self.repo_context = repo_context
        self.temp_dir = Path(temp_dir)
        self.md = self.config.md
        self.git = self.config.git
        self.repo_url = (
            self.git.repository
            if self.git.host_domain != GitHost.LOCAL.name.lower()
            else f"../{self.git.name}"
        )
        self.header_template = HeaderTemplate(self.md.header_style)
        self.table_of_contents = self.md.table_of_contents

    @property
    def header_and_badges(self) -> str:
        """Generates the README header section."""

        if BadgeStyleOptions.SKILLS.value not in self.md.badge_style:
            md_shields, md_badges = badges.shieldsio_icons(
                self.config,
                self.deps,
                str(self.git.full_name),
                str(self.git.host),
            )
        else:
            md_shields = (
                "<!-- Shields.io badges disabled, using skill icons. -->"
            )
            md_badges = badges.skill_icons(self.config, self.deps)

        header_data = {
            "align": self.md.align,
            "image": self.md.image,
            "image_width": self.md.image_width,
            "repo_name": self.git.name.upper()
            if self.git.name
            else self.md.placeholder,
            "shields_icons": md_shields,
            "badges_tech_stack": md_badges,
            "badges_tech_stack_text": self.md.badges_tech_stack_text,
        }
        return self.header_template.render(header_data)

    @property
    def quickstart_guide(self) -> str:
        """Generates the README Getting Started section."""
        return QuickStartBuilder(self.config_loader, self.repo_context).build()

    @property
    def contributing_guide(self) -> str:
        """Generates the README Contributing section."""
        return self.md.contribute.format(
            host=self.git.host,
            host_domain=self.git.host_domain,
            full_name=self.git.full_name,
            repo_name=self.git.name,
            repo_url=self.repo_url,
        )

    def build(self) -> str:
        """Builds each section of the README.md file."""
        readme_md_contents = [
            self.header_and_badges,
            self.md.overview,
            self.table_of_contents,
            self.md.core_features,
            self.quickstart_guide,
            self.contributing_guide,
        ]

        return "\n".join(readme_md_contents)
