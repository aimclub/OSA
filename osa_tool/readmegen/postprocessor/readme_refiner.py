import json
import re

from osa_tool.config.settings import ConfigLoader
from osa_tool.readmegen.models.llm_service import LLMClient


class ReadmeRefiner:
    def __init__(self, config_loader: ConfigLoader, new_readme: str):
        self.config_loader = config_loader
        self.config = self.config_loader.config
        self.new_readme = new_readme
        self.llm_client = LLMClient(self.config_loader)

    def refine(self) -> str:
        """
        Refines the generated README by merging it with the original content via LLM.

        Returns:
            str: The final refined README content in markdown format.
        """
        new_readme_sections = self.parse_generated_readme()
        response = self.llm_client.refine_readme(new_readme_sections)

        response_dict = json.loads(response)
        return self.build_readme_from_sections(response_dict)

    def parse_generated_readme(self) -> dict:
        """
        Parses the generated README into sections based on markdown headers.

        Returns:
            dict: A dictionary with section titles as keys and their content as values.
                  The 'badges' section includes all content before the first '## ' header.
        """
        sections = {}
        lines = self.new_readme.splitlines()

        current_section = "badges"
        sections[current_section] = ""

        for line in lines:
            if re.match(r"^\s*##\s+", line):
                current_section = line.strip("# ").strip()
                sections[current_section] = ""
            else:
                sections[current_section] += line + "\n"

        for key in sections:
            sections[key] = sections[key].strip()

        return sections

    @staticmethod
    def build_readme_from_sections(sections: dict) -> str:
        """
        Assembles the final README markdown content from JSON-like sections preserving their order.

        Args:
            sections (dict): A dictionary where keys are section titles and values are section content.

        Returns:
            str: The assembled README content in Markdown format.
        """
        readme_parts = []
        for key, content in sections.items():
            if not content.strip():
                continue

            if key == "badges":
                readme_parts.append(content.strip())
            else:
                readme_parts.append(f"## {key}\n\n{content.strip()}")

        final_readme = "\n\n".join(readme_parts)
        return final_readme
