from OSA.readmeai.readmegen_article.config.settings import ArticleConfigLoader
from OSA.readmeai.readmegen_article.templates.header import ArticleHeaderTemplate


class ArticleMarkdownBuilder:
    """
    Builds each section of the README Markdown file.
    """

    def __init__(
            self,
            config_loader: ArticleConfigLoader
    ):
        self.config_loader = config_loader
        self.config = config_loader.config
        self.md = self.config.md
        self.git = self.config.git
        self.header_template = ArticleHeaderTemplate(self.md.header_style)

    @property
    def header(self) -> str:
        """Generates the README header section."""
        header_data = {
            "align": self.md.align,
            "image": self.md.image,
            "image_width": self.md.image_width,
            "repo_name": (
                self.git.name.upper() if self.git.name else self.md.placeholder
            ),
        }
        return self.header_template.render(header_data)


    def build(self) -> str:
        """Builds each section of the README.md file."""
        readme_md_contents = [
            self.header,
            self.md.overview,
            self.md.content,
            self.md.algorithms,
        ]

        return "\n".join(readme_md_contents)
