from pathlib import Path

from readmegen.config.settings import ConfigLoader
from readmegen.generators import badges
from readmegen.ingestion.models import RepositoryContext
from readmegen.readers.git.providers import GitHost
from readmegen.templates.header import HeaderTemplate
from readmegen.templates.quickstart import QuickStartBuilder
from readmegen.templates.contributing import ContributingBuilder
from readmegen.readers.git.metadata import fetch_git_repository_metadata


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
        self.docs = repo_context.docs_paths
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
        self.metadata = fetch_git_repository_metadata(self.repo_url)

    @property
    def header_and_badges(self) -> str:
        """Generates the README header section."""
        md_shields, md_badges = badges.shieldsio_icons(
            self.config,
            self.deps,
            str(self.git.full_name),
            str(self.git.host),
        )

        header_data = {
            "align": self.md.align,
            "image": self.md.image,
            "image_width": self.md.image_width,
            "repo_name": (
                self.git.name.upper() if self.git.name else self.md.placeholder
            ),
            "shields_icons": md_shields,
            "badges_tech_stack": md_badges,
            "badges_tech_stack_text": self.md.badges_tech_stack_text,
        }
        return self.header_template.render(header_data)

    @property
    def installation_guide(self) -> str:
        """Generates the README Installation section."""
        return QuickStartBuilder(
            self.config_loader, self.repo_context
        ).build_installation_section()

    @property
    def getting_started_guide(self) -> str:
        """Generates the README Getting Started section."""
        return QuickStartBuilder(
            self.config_loader, self.repo_context
        ).build_usage_section()

    @property
    def examples(self) -> str:
        """Generates the README Examples section"""
        examples_path = ""
        examples_name = "examples"
        if "examples" in self.docs:
            examples_path = "examples"
        else:
            examples_name = "Not found any examples"

        return self.md.examples.format(
            examples=examples_name,
            default_branch=self.metadata.default_branch,
            host_domain=self.git.host_domain,
            full_name=self.git.full_name,
            examples_path=examples_path,
        )

    @property
    def contributing(self) -> str:
        """Generates the README Contributing section."""
        return ContributingBuilder(
            self.config_loader, self.repo_context
        ).build()

    @property
    def license(self) -> str:
        """Generates the README License section"""
        license_path = self.metadata.license_url
        for path in self.docs:
            if path.startswith("LICENSE"):
                license_path = path
                break

        return self.md.license.format(
            license_name=self.metadata.license_name,
            default_branch=self.metadata.default_branch,
            host_domain=self.git.host_domain,
            full_name=self.git.full_name,
            license_path=license_path,
        )

    @property
    def documentation(self) -> str:
        """Generates the README Documentation section"""
        homepage_url = self.metadata.homepage_url
        docs = "docs"
        if not homepage_url:
            if "docs" in self.docs:
                homepage_url = (f"https://{self.git.host_domain}/"
                                f"{self.git.full_name}/tree/"
                                f"{self.metadata.default_branch}/docs")
            else:
                docs = "Not found any docs"

        return self.md.documentation.format(
            repo_name=self.git.name, docs=docs, homepage_url=homepage_url
        )

    @property
    def contacts(self) -> str:
        """Generates the README Contacts section"""
        return self.md.contacts

    @property
    def acknowledgments(self) -> str:
        """Generates the README Contacts section"""
        return self.md.acknowledgments

    def build(self) -> str:
        """Builds each section of the README.md file."""
        readme_md_contents = [
            self.header_and_badges,
            self.md.overview,
            self.table_of_contents,
            self.md.core_features,
            self.installation_guide,
            self.examples,
            self.documentation,
            self.getting_started_guide,
            self.contributing,
            self.license,
            self.acknowledgments,
            self.contacts,
        ]

        return "\n".join(readme_md_contents)
