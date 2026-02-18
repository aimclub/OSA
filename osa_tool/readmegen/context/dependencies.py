import os
import re

import tomli

from osa_tool.readmegen.utils import find_in_repo_tree
from osa_tool.utils import logger


class DependencyExtractor:
    """
    A utility class for extracting technology dependencies from common Python project files
    such as requirements.txt, pyproject.toml, and setup.py within a given repository.
    """

    def __init__(self, tree: str, base_path: str):
        """
        Initializes a dependency parser with the given project tree and base path.
        
        Args:
            tree: The root directory or identifier of the project tree to analyze.
            base_path: The base filesystem path where the project resides.
        
        Attributes:
            tree: Stores the project tree identifier or path.
            base_path: Stores the base filesystem path for the project.
            regex_requirements: Regular expression pattern used to match package names in
                requirements files.
            regex_setup_install_requires: Regular expression pattern used to extract the
                `install_requires` list from a setup.py file.
            regex_setup_python_requires: Regular expression pattern used to extract the
                `python_requires` specification from a setup.py file.
            regex_setup_dependency_items: Regular expression pattern used to capture
                individual dependency items within the `install_requires` list.
        
        Returns:
            None
        """
        self.tree = tree
        self.base_path = base_path

        # Regular expressions for matching dependencies in various files
        self.regex_requirements = r"^\s*([a-zA-Z0-9_\-]+)"
        self.regex_setup_install_requires = r"install_requires\s*=\s*\[([^]]+)]"
        self.regex_setup_python_requires = r"python_requires\s*=\s*['\"]([^'\"]+)['\"]"
        self.regex_setup_dependency_items = r"'([^']+)'|\"([^\"]+)\""

    def extract_techs(self) -> set[str]:
        """
        Extracts a set of technologies used in the repository based on declared dependencies.

        Returns:
            set[str]: A set of technology names found in dependency files.
        """
        techs = set()

        techs.update(self._extract_from_requirements())
        techs.update(self._extract_from_pyproject())
        techs.update(self._extract_from_setup())
        return techs

    def extract_python_version_requirement(self) -> str | None:
        """
        Extracts the Python version requirement from pyproject.toml or setup.py.

        Returns:
            str | None: Version specifier (e.g. ">=3.7") or None if not found.
        """
        pyproject_path = self._find_file(r"pyproject\.toml")
        if pyproject_path:
            try:
                with open(pyproject_path, "rb") as f:
                    data = tomli.load(f)

                # PEP 621
                version = data.get("project", {}).get("requires-python")
                if version:
                    return version.strip()

                # Poetry format
                poetry_info = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
                if "python" in poetry_info:
                    python_spec = poetry_info["python"]
                    return python_spec.strip() if isinstance(python_spec, str) else None

            except tomli.TOMLDecodeError:
                logger.warning("Failed to parse pyproject.toml")

        setup_path = self._find_file(r"setup\.py")
        if setup_path:
            try:
                with open(setup_path, encoding="utf-8") as f:
                    content = f.read()

                match = re.search(self.regex_setup_python_requires, content)
                if match:
                    return match.group(1).strip()

            except Exception as e:
                logger.warning(f"Failed to parse setup.py: {e}")

        return None

    def _extract_from_requirements(self) -> set[str]:
        """
        Parses `requirements.txt` for listed dependencies.

        Returns:
            set[str]: A set of dependency names.
        """
        path = self._find_file("requirements\\.txt")
        if not path:
            return set()

        techs = set()
        encodings_to_try = ["utf-8", "utf-16", "latin-1"]

        for encoding in encodings_to_try:
            try:
                with open(path, encoding=encoding) as file:
                    for line in file:
                        match = re.match(self.regex_requirements, line)
                        if match:
                            techs.add(match.group(1).lower())
                    break
            except UnicodeDecodeError:
                continue
        else:
            logger.error(f"Could not decode {path} using known encodings.")

        return techs

    def _extract_from_pyproject(self) -> set[str]:
        """
        Parses `pyproject.toml` to extract dependencies from both PEP 621 and Poetry sections.

        Returns:
            set[str]: A set of dependency names.
        """
        path = self._find_file("pyproject\\.toml")
        if not path:
            return set()

        techs = set()
        with open(path, "rb") as f:
            try:
                data = tomli.load(f)

                # PEP 621
                deps = data.get("project", {}).get("dependencies", [])
                techs.update(self._normalize_dependency(dep) for dep in deps)

                # Poetry
                poetry_deps = data.get("tool", {}).get("poetry", {}).get("dependencies", {})
                techs.update(name.lower() for name in poetry_deps.keys())

            except tomli.TOMLDecodeError:
                logger.error("Failed to decode pyproject.toml")
                pass
        return techs

    def _extract_from_setup(self) -> set[str]:
        """
        Parses `setup.py` to extract dependencies listed in `install_requires`.

        Returns:
            set[str]: A set of dependency names.
        """
        path = self._find_file("setup\\.py")
        if not path:
            return set()

        techs = set()

        with open(path, encoding="utf-8") as f:
            content = f.read()

        match = re.search(self.regex_setup_install_requires, content, re.DOTALL)
        if match:
            items = re.findall(self.regex_setup_dependency_items, match.group(1))
            for item in items:
                dep = next(filter(None, item))
                techs.add(dep.split()[0].lower())
        return techs

    @staticmethod
    def _normalize_dependency(dep: str) -> str:
        """
        Normalize a dependency string.
        
        This static method processes a dependency string by extracting the first
        token before any whitespace or semicolon, trimming surrounding whitespace,
        and converting the result to lowercase. It is useful for standardizing
        dependency identifiers that may contain version constraints or comments.
        
        Args:
            dep: The dependency string to normalize.
        
        Returns:
            str: The normalized dependency string.
        """
        return dep.split()[0].split(";")[0].strip().lower()

    def _find_file(self, pattern: str) -> str | None:
        """
        Find the absolute path of a file matching a given pattern within the repository tree.
        
        Args:
            pattern: A regular expression pattern to search for in the repository tree.
        
        Returns:
            str or None: The absolute path to the first file that matches the pattern, or ``None`` if no match is found.
        
        The method uses :func:`find_in_repo_tree` to locate a relative file path that matches the supplied pattern in the string representation of the repository tree stored in ``self.tree``. If a match is found, the relative path is joined with ``self.base_path`` to produce an absolute path. If no match is found, the method returns ``None``.
        """
        rel_path = find_in_repo_tree(self.tree, pattern)
        if rel_path:
            abs_path = os.path.join(self.base_path, rel_path)
            return abs_path
        return None
