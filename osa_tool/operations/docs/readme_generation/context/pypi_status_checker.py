import os
import re

import requests
import tomli

from osa_tool.operations.docs.readme_generation.utils import find_in_repo_tree, read_file
from osa_tool.utils.logger import logger


class PyPiPackageInspector:
    """
    PyPiPackageInspector inspects Python projects to determine if they are published on PyPI and retrieves related metadata.
    
        Methods:
            __init__: Initializes the instance with project metadata and API configuration.
            get_info: Retrieves PyPI publication info including name, version, and download count.
            get_published_package_name: Checks whether a package defined in a file in the repo tree is published on PyPI.
            _extract_package_name_from_pyproject: Attempts to extract the package name from the contents of pyproject.toml.
            _extract_package_name_from_setup: Tries to extract the package name from the contents of setup.py (roughly, via regular expression).
            _is_published_on_pypi: Checks if a package is published on PyPI by its name.
            _get_package_version_from_pypi: Retrieves version of the package from PyPI.
            _get_downloads_from_pepy: Retrieves the total downloads count for the package using pepy.tech API.
    
        Attributes:
            tree: Stores the project tree structure.
            base_path: Stores the base directory path for file operations.
            api_key: The API key retrieved from the 'X-API-Key' environment variable.
            patterns_for_file: A list of regex patterns used to identify relevant configuration files.
            pattern_for_setup: A regex pattern used to extract the package name from setup files.
            pypi_url_template: The URL template for fetching package data from PyPI.
            pepy_url_template: The URL template for fetching download statistics from PePy.
    
        The class primarily facilitates checking publication status on PyPI and gathering associated data like version and download statistics. Its methods handle extraction of package names from configuration files, API requests to PyPI and PePy, and consolidation of this information. The attributes store configuration, paths, and patterns necessary for these operations.
    """

    def __init__(self, tree: str, base_path: str):
        """
        Initialize the instance with project metadata and API configuration.
        
        Args:
            tree: The directory structure or tree representation of the project.
            base_path: The root filesystem path where the project is located.
        
        Attributes:
            tree: Stores the project tree structure.
            base_path: Stores the base directory path for file operations.
            api_key: The API key retrieved from the 'X-API-Key' environment variable, used for authenticated API requests.
            patterns_for_file: A list of regex patterns used to identify relevant configuration files (pyproject.toml and setup.py).
            pattern_for_setup: A regex pattern used to extract the package name from setup files.
            pypi_url_template: The URL template for fetching package data from PyPI.
            pepy_url_template: The URL template for fetching download statistics from PePy.
        
        Why:
            This initializer sets up the inspector with necessary paths, environment configurations, and predefined patterns to later locate and analyze Python package metadata, fetch data from PyPI and PePy APIs, and extract the package name from configuration files.
        """
        self.tree = tree
        self.base_path = base_path
        self.api_key = os.getenv("X-API-Key")
        self.patterns_for_file = [r"pyproject\.toml", r"setup\.py"]
        self.pattern_for_setup = r"(?i)(?:^|\s)name\s*=\s*['\"]([^'\"]+)['\"]"
        self.pypi_url_template = "https://pypi.org/pypi/{package}/json"
        self.pepy_url_template = "https://api.pepy.tech/api/v2/projects/{package}"

    def get_info(self) -> dict | None:
        """
        Retrieves PyPI publication info including name, version, and download count.
        
        This method first determines if the repository's package is published on PyPI. If published, it fetches the latest version from PyPI and the total download count from the pepy.tech API, then compiles this information into a dictionary.
        
        Returns:
            dict | None: A dictionary with keys "name" (the published package name), "version" (the latest version from PyPI), and "downloads" (the total download count from pepy.tech). Returns None if the package is not published on PyPI.
        """
        package_name = self.get_published_package_name()
        if not package_name:
            return None

        version = self._get_package_version_from_pypi(package_name)
        downloads = self._get_downloads_from_pepy(package_name)

        return {"name": package_name, "version": version, "downloads": downloads}

    def get_published_package_name(self) -> str | None:
        """
        Checks whether a package defined in a file in the repository tree is published on PyPI.
        
        The method searches the repository tree for specific configuration files (pyproject.toml or setup.py) using predefined patterns. For each found file, it extracts the package name and verifies its publication status on PyPI. This is used to determine if the repository's package is publicly available for installation.
        
        Args:
            patterns_for_file: A list of regex patterns used to locate package configuration files in the repository tree.
            base_path: The root directory path of the repository, used to construct absolute file paths.
            tree: A string representation of the repository's file structure.
        
        Returns:
            The name of the published package if a configuration file is found, the package name is successfully extracted, and the package is confirmed to be published on PyPI. Otherwise, None.
        
        Why:
            This method enables the tool to identify publicly released Python packages within a repository, which is essential for accurate documentation generation and repository analysis. It handles multiple packaging standards (PEP 621 and Poetry via pyproject.toml, and legacy setup.py) and gracefully skips files that cannot be read or parsed.
        """
        for pattern in self.patterns_for_file:
            file = find_in_repo_tree(self.tree, pattern)

            if not file:
                continue

            file_path = os.path.join(self.base_path, file)
            try:
                content = read_file(file_path)
            except Exception as e:
                logger.error(f"Error while reading {file_path}: {e}")
                continue

            package_name = None
            if file_path.endswith("pyproject.toml"):
                package_name = self._extract_package_name_from_pyproject(content)
            elif file_path.endswith("setup.py"):
                package_name = self._extract_package_name_from_setup(content)

            if package_name and self._is_published_on_pypi(package_name):
                return package_name

        return None

    @staticmethod
    def _extract_package_name_from_pyproject(content: str) -> str | None:
        """
        Attempts to extract the package name from the contents of a pyproject.toml file.
        
        The method supports multiple common project configurations: first checking the PEP 621 standard `[project]` table, then falling back to the Poetry-specific `[tool.poetry]` table. This ensures compatibility with a wide range of Python packaging tools.
        
        Args:
            content: The raw string content of the pyproject.toml file.
        
        Returns:
            str | None: The extracted package name if found in a supported section; otherwise None.
        
        Why:
            If the TOML content cannot be parsed, an error is logged and None is returned.
            If no package name is located in either of the checked sections, a warning is logged.
        """
        try:
            data = tomli.loads(content)
        except tomli.TOMLDecodeError:
            logger.error("Failed to decode pyproject.toml")
            return None

        # Try PEP 621-style [project]
        name = data.get("project", {}).get("name")
        if name:
            return name

        # Try Poetry-style [tool.poetry]
        name = data.get("tool", {}).get("poetry", {}).get("name")
        if name:
            return name

        logger.warning("Package name not found in pyproject.toml")
        return None

    def _extract_package_name_from_setup(self, content: str) -> str | None:
        """
        Tries to extract the package name from the contents of setup.py using a regular expression pattern.
        
        This method is used as a fallback when more reliable metadata sources (like pyproject.toml or PKG-INFO) are unavailable. It performs a rough extraction because setup.py is executable code, making precise parsing difficult without full evaluation.
        
        Args:
            content: The content of the setup.py file as a string.
        
        Returns:
            str | None: The extracted package name if found, otherwise None. Returns None and logs a warning if no match is found.
        """
        match = re.search(self.pattern_for_setup, content)
        if match:
            return match.group(1)
        else:
            logger.warning("Package name not found in setup.py")
            return None

    def _is_published_on_pypi(self, package_name: str) -> bool:
        """
        Checks if a package is published on PyPI by its name.
        
        This method attempts to fetch the package's metadata page from PyPI using a formatted URL template. It determines publication status based on whether the HTTP request returns a successful response (status code 200). If the request fails due to a network or connection error, the method logs the error and treats the package as not published.
        
        Args:
            package_name: The name of the package to check.
        
        Returns:
            bool: True if the package is published on PyPI (HTTP 200), False otherwise.
        """
        url = self.pypi_url_template.format(package=package_name)
        try:
            response = requests.get(url)
            return response.status_code == 200
        except requests.RequestException as e:
            logger.error(f"Request to PyPI failed: {e}")
        return False

    def _get_package_version_from_pypi(self, package_name: str) -> str | None:
        """
        Retrieves the latest version of a package from PyPI by querying its JSON metadata API.
        
        WHY: This method provides a fallback mechanism to obtain version information when local package metadata is unavailable, ensuring the inspector can report accurate version data even for packages not installed in the current environment.
        
        Args:
            package_name: The name of the package to look up on PyPI.
        
        Returns:
            str | None: The latest version string of the package if the request succeeds and the version field is present; otherwise, None if the HTTP request fails, returns a non‑200 status, or the version key is missing from the response.
        """
        url = self.pypi_url_template.format(package=package_name)
        try:
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get("info", {}).get("version")
        except requests.RequestException as e:
            logger.error(f"Failed to fetch metadata from PyPI: {e}")
        return None

    def _get_downloads_from_pepy(self, package_name: str) -> int | None:
        """
        Retrieves the total downloads count for a package using the pepy.tech API.
        
        This method is used as a fallback or alternative source for download statistics when primary sources are unavailable or fail. It makes an authenticated HTTP GET request to the pepy.tech service to fetch the total downloads for the specified package.
        
        Args:
            package_name: The name of the package to query.
        
        Returns:
            int | None: The total number of downloads retrieved from the API, or None if the request fails due to a non-200 status code or a network exception. In case of failure, an error is logged.
        
        Note:
            The request includes an API key header for authentication. The method expects the API response to be a JSON object containing a 'total_downloads' field.
        """
        url = self.pepy_url_template.format(package=package_name)
        headers = {"X-API-Key": f"{self.api_key}"}

        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                return data.get("total_downloads")
            else:
                logger.error(f"Request failed for {package_name}. Status code: {response.status_code}. URL: {url}")
        except requests.RequestException as e:
            logger.error(f"Failed to fetch download stats from pepy.tech: {e}")
        return None
