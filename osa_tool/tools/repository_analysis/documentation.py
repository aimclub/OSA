import re
from pathlib import Path


class DocumentationAnalyzer:
    """
    Detects presence of documentation-related artifacts in a repo tree
        and extracts README summary text.
    """


    def __init__(self, repo_path: str, tree: str):
        """
        Initialize a new instance of the DocumentationAnalyzer with a repository path and a tree reference.
        
        Args:
            repo_path: The file system path to the repository. It will be converted to a Path object internally.
            tree: The specific tree or branch reference (e.g., a branch name, tag, or commit hash) within the repository.
        
        Attributes:
            repo_path: A Path object representing the location of the repository.
            tree: A string representing the tree or branch reference.
        
        Why:
            The repository path is converted to a Path object to facilitate filesystem operations and ensure cross-platform compatibility. The tree reference is stored as-is to be used later for checking out or analyzing a specific state of the repository.
        """
        self.repo_path = Path(repo_path)
        self.tree = tree

    def analyze(self) -> dict:
        """
        Analyzes the repository's documentation structure and key files.
        
        Scans the repository for common documentation files and configuration files,
        returning a dictionary with boolean flags indicating their presence and a
        readme excerpt.
        
        WHY: This analysis helps assess the completeness and accessibility of a repository's documentation, which is crucial for user onboarding, project maintenance, and overall project health.
        
        Returns:
            dict: A dictionary containing analysis results with the following keys:
                has_readme (bool): Whether a README file exists (case-insensitive match).
                has_license (bool): Whether a LICENSE file exists (case-insensitive match, accepts "LICENSE" or "LICENCE").
                has_docs_folder (bool): Whether a documentation folder exists (matches common names like docs, documentation, wiki, or manuals).
                has_examples (bool): Whether examples or tutorials exist (matches folders like tutorials, examples, or notebooks).
                has_contributing (bool): Whether a contributing guidelines file exists (matches filenames containing "contribut" with .md, .rst, or .txt extension).
                has_citation (bool): Whether a CITATION file exists (case-insensitive match).
                has_requirements (bool): Whether a requirements file exists (case-insensitive match, e.g., requirements.txt).
                has_pyproject (bool): Whether a pyproject.toml file exists.
                has_setup (bool): Whether a setup.py or setup.cfg file exists.
                readme_excerpt (str): A cleaned, truncated plain-text excerpt from the README, or None if no README is found or an error occurs.
        """
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
        """
        Checks if a given regular expression pattern matches the internal tree string.
        
        Args:
            pattern: The regular expression pattern to search for within the tree.
        
        Returns:
            bool: True if the pattern is found anywhere in the tree string (case-insensitive), False otherwise.
        
        Why:
            This method supports searching for patterns within the parsed documentation tree, enabling flexible content analysis and validation without requiring exact string matches.
        """
        return bool(re.search(pattern, self.tree, re.IGNORECASE))

    def _extract_readme_excerpt(self, max_chars: int = 1500) -> str | None:
        """
        Extracts a cleaned, truncated text version of a README file from the repository.
        
        Searches the repository for any file with a name starting with "README" (case-insensitive). If found, the file is read as UTF-8 text, cleaned of Markdown and HTML formatting to produce plain text, and then truncated to a maximum character limit. If the file cannot be read or processed, or if no README is found, the method returns None.
        
        WHY: This provides a concise, plain-text excerpt of the README suitable for summaries, previews, or further text analysis where formatting is not needed.
        
        Args:
            max_chars: Maximum number of characters to return after cleaning. Defaults to 1500.
        
        Returns:
            The cleaned and truncated plain text of the README, or None if no README is found or an error occurs during reading/processing.
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
        """
        Removes Markdown formatting and HTML tags from a string to produce plain text.
        
        This method uses regular expressions to strip out images, links (keeping the link text), headers, inline code blocks, and HTML tags. It also collapses multiple whitespace characters into a single space and trims leading/trailing whitespace.
        
        WHY: This cleaning process is essential for converting formatted documentation or content into plain text, which is easier to analyze, compare, or use in contexts where formatting is irrelevant (e.g., text similarity checks, summarization, or plain text exports).
        
        Args:
            text: The string containing Markdown content to be cleaned.
        
        Returns:
            str: The processed string with Markdown and HTML elements removed.
        """
        text = re.sub(r"!\[.*?\]\(.*?\)", "", text)  # images
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links
        text = re.sub(r"#+\s*", "", text)  # headers
        text = re.sub(r"`{1,3}[^`]*`{1,3}", "", text)  # inline code
        text = re.sub(r"<[^>]+>", "", text)  # html tags
        text = re.sub(r"\s+", " ", text)
        return text.strip()
