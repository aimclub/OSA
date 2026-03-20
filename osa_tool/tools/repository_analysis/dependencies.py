import os
import re

import tomli

from osa_tool.operations.docs.readme_generation.utils import find_in_repo_tree
from osa_tool.utils.logger import logger


class DependencyExtractor:
    """
    A utility class for extracting technology dependencies from common Python project files
        such as requirements.txt, pyproject.toml, and setup.py within a given repository.
    """


    def __init__(self, tree: str, base_path: str):
        """
        Initializes a new instance of the DependencyExtractor class with the provided tree structure and base path.
        
        Args:
            tree: The tree structure representing the project or directory, used to navigate and locate dependency files.
            base_path: The base directory path used for file operations and dependency lookups.
        
        Attributes:
            tree: Stores the project tree structure.
            base_path: Stores the base path for dependency lookups.
            regex_requirements: A regular expression for parsing package names from requirements.txt files.
            regex_setup_install_requires: A regular expression for extracting the install_requires list from setup.py files.
            regex_setup_python_requires: A regular expression for extracting the python_requires version from setup.py files.
            regex_setup_dependency_items: A regular expression for matching individual dependency strings within a list.
        
        Why:
            The regular expressions are compiled and stored as instance attributes to efficiently parse different dependency specification formats (requirements.txt and setup.py) across the project. This avoids recompiling patterns repeatedly during extraction.
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
        Extracts a set of technologies used in the repository based on declared dependencies from multiple Python dependency files.
        
        The method consolidates results from three helper methods, each parsing a specific file type: `requirements.txt`, `pyproject.toml`, and `setup.py`. This ensures comprehensive detection of dependencies across common Python packaging configurations and legacy setups.
        
        Why:
        - Different Python projects use different files to declare dependencies. By checking all three sources, the method provides a complete view of the technologies a repository depends on.
        - This approach supports automated repository analysis by capturing dependencies regardless of the project's chosen packaging method.
        
        Returns:
            A set of technology names (dependency names) found across all scanned dependency files. The set may be empty if no supported dependency files are found or if they contain no extractable dependencies.
        """
        techs = set()

        techs.update(self._extract_from_requirements())
        techs.update(self._extract_from_pyproject())
        techs.update(self._extract_from_setup())
        return techs

    def extract_python_version_requirement(self) -> str | None:
        """
        Extracts the Python version requirement from pyproject.toml or setup.py.
        
        The method searches for these files in the repository using a case-insensitive pattern match.
        It first attempts to read and parse pyproject.toml, checking for the Python version in two common locations:
        1. Under the PEP 621 `project.requires-python` key.
        2. Under the Poetry-specific `tool.poetry.dependencies.python` key.
        If pyproject.toml is not found or cannot be parsed, it falls back to searching setup.py for a `python_requires` pattern.
        If neither file yields a valid version specifier, the method returns None.
        
        Returns:
            str | None: Version specifier (e.g., ">=3.7") or None if not found.
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
        
        Why:
            The method attempts to locate and read a `requirements.txt` file within the repository, handling potential encoding issues. It uses a regular expression to extract dependency names from each line, ignoring those that do not match the pattern (e.g., comments, blank lines, or version specifiers). Multiple encodings are tried to accommodate files that may not be saved in standard UTF-8.
        
        Args:
            None.
        
        Returns:
            A set of dependency names extracted from the file. If the file is not found or cannot be decoded, an empty set is returned.
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
        
        The method searches for the file in the repository, then extracts and normalizes dependency names from two standard locations: the PEP 621 `project.dependencies` list and the Poetry `tool.poetry.dependencies` dictionary. This ensures comprehensive dependency detection across common Python packaging configurations.
        
        Args:
            None.
        
        Returns:
            set[str]: A set of normalized dependency names. Returns an empty set if the file is not found or cannot be decoded.
        
        Why:
            Python projects can declare dependencies in different sections of `pyproject.toml` depending on the build system and tooling used. This method consolidates extraction from multiple common sources to provide a complete view of declared dependencies.
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
        Parses `setup.py` to extract dependencies listed in the `install_requires` argument.
        
        The method searches for a `setup.py` file in the repository and uses regular expressions to locate the `install_requires` list. Each dependency name is normalized to lowercase and its version specifier (if present) is stripped, returning only the base package name.
        
        Why:
        - This extraction supports automated dependency analysis by reading traditional Python setup files, which may not be covered by other manifest formats like `pyproject.toml` or `requirements.txt`.
        - The method handles potential parsing errors gracefully to avoid interrupting the overall analysis process.
        
        Args:
            pattern: Not a direct parameter. Internally uses a regex pattern (`self.regex_setup_install_requires`) to find the `install_requires` section and another (`self.regex_setup_dependency_items`) to extract individual dependency items.
        
        Returns:
            A set of dependency names (strings). Returns an empty set if `setup.py` is not found or if parsing fails.
        """
        path = self._find_file("setup\\.py")
        if not path:
            return set()

        techs = set()

        try:
            with open(path, encoding="utf-8") as f:
                content = f.read()
            match = re.search(self.regex_setup_install_requires, content, re.DOTALL)
            if match:
                items = re.findall(self.regex_setup_dependency_items, match.group(1))
                for item in items:
                    dep = next(filter(None, item))
                    techs.add(dep.split()[0].lower())
        except Exception as e:
            logger.error(f"Failed to parse setup.py: {e}")

        return techs

    @staticmethod
    def _normalize_dependency(dep: str) -> str:
        """
        Normalizes a dependency string by extracting the core package name.
        
        This method processes a dependency string by removing version specifiers,
        environment markers, and extra whitespace, then converting the result
        to lowercase. It is used to standardize dependency names for consistent
        comparison and lookup within the OSA Tool's dependency analysis pipeline.
        
        Args:
            dep: The raw dependency string to be normalized (e.g., "requests>=2.25.0; python_version>='3.6'").
        
        Returns:
            str: The normalized dependency name (e.g., "requests").
        """
        return dep.split()[0].split(";")[0].strip().lower()

    def _find_file(self, pattern: str) -> str | None:
        """
        Searches for a file in the repository tree matching a given pattern.
        
        Args:
            pattern: A regular expression pattern to search for in the repository tree.
                The search is performed case-insensitively.
        
        Returns:
            The absolute path to the first matching file if found, otherwise None.
        
        Why:
            This method is used to locate specific files (like dependency manifests or configuration files)
            within the repository structure. It converts a relative match from the tree representation into
            an absolute path, ensuring the result is usable for further file operations.
        """
        rel_path = find_in_repo_tree(self.tree, pattern)
        if rel_path:
            abs_path = os.path.join(self.base_path, rel_path)
            return abs_path
        return None
