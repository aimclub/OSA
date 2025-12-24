import re
from pathlib import Path


class DocumentationAnalyzer:
    """
    Detects presence of documentation-related artifacts in a repo tree
    and extracts README summary text.
    """

    def __init__(self, repo_path: str, tree: str):
        self.repo_path = Path(repo_path)
        self.tree = tree

    def analyze(self) -> dict:
        doc_info = {
            "has_readme": self._match(r"\bREADME(\.\w+)?\b"),
            "has_license": self._match(r"\bLICEN[SC]E(\.\w+)?\b"),
            "has_docs_folder": self._match(r"\b(docs?|documentation|wiki|manuals?)\b"),
            "has_examples": self._match(r"\b(tutorials?|examples|notebooks?)\b"),
            "has_contributing": self._match(r"\b\w*contribut\w*\.(md|rst|txt)$"),
            "has_citation": self._match(r"\bCITATION(\.\w+)?\b"),
            "has_requirements": self._match(r"\brequirements(\.\w+)?\b"),
            "has_pyproject": self._match(r"\bpyproject\.toml\b"),
            "has_setup": self._match(r"\bsetup\.(py|cfg)\b"),
            "readme_excerpt": self._extract_readme_excerpt(),
        }
        return doc_info

    def _match(self, pattern: str) -> bool:
        return bool(re.search(pattern, self.tree, re.IGNORECASE))

    def _extract_readme_excerpt(self, max_chars: int = 1500) -> str | None:
        """
        Extracts a cleaned, truncated text version of README.
        """
        readme_path = next((p for p in self.repo_path.rglob("README*") if p.is_file()), None)
        if not readme_path:
            return None
        try:
            text = readme_path.read_text(encoding="utf-8", errors="ignore")
            text = self._clean_markdown(text)
            return text[:max_chars].strip()
        except Exception:
            return None

    @staticmethod
    def _clean_markdown(text: str) -> str:
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)  # images
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links
        text = re.sub(r"#+\s*", "", text)  # headers
        text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)  # inline code
        text = re.sub(r"<[^>]+>", "", text)  # html tags
        text = re.sub(r"\s+", " ", text)
        return text.strip()
