import os
import re

from osa_tool.config.settings import ConfigLoader
from osa_tool.utils import get_repo_tree, parse_folder_name


class SourceRank:

    def __init__(self, config_loader: ConfigLoader):
        self.config = config_loader.config
        self.repo_url = self.config.git.repository
        self.repo_path = os.path.join(os.getcwd(), parse_folder_name(self.repo_url))
        self.tree = get_repo_tree(self.repo_path)

    def readme_presence(self) -> bool:
        pattern = re.compile(r"\bREADME(\.\w+)?\b", re.IGNORECASE)
        return bool(pattern.search(self.tree))

    def license_presence(self) -> bool:
        pattern = re.compile(r"\bLICEN[SC]E(\.\w+)?\b", re.IGNORECASE)
        return bool(pattern.search(self.tree))

    def examples_presence(self) -> bool:
        pattern = re.compile(r"\b(tutorials?|examples|notebooks?)\b", re.IGNORECASE)
        return bool(pattern.search(self.tree))

    def docs_presence(self) -> bool:
        pattern = re.compile(r"\b(docs?|documentation|wiki|manuals?)\b", re.IGNORECASE)
        return bool(pattern.search(self.tree))

    def tests_presence(self) -> bool:
        pattern = re.compile(r"\b(tests?|testcases?|unittest|test_suite)\b", re.IGNORECASE)
        return bool(pattern.search(self.tree))

    def citation_presence(self) -> bool:
        pattern = re.compile(r"\bCITATION(\.\w+)?\b", re.IGNORECASE)
        return bool(pattern.search(self.tree))

    def contributing_presence(self) -> bool:
        pattern = re.compile(r"\b\w*contribut\w*\.(md|rst|txt)$", re.IGNORECASE)
        return bool(pattern.search(self.tree))

    def requirements_presence(self) -> bool:
        pattern = re.compile(r"\brequirements(\.\w+)?\b", re.IGNORECASE)
        return bool(pattern.search(self.tree))
