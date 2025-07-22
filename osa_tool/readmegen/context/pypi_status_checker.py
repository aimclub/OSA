import os
import re

import requests
import tomli

from osa_tool.readmegen.utils import find_in_repo_tree, read_file
from osa_tool.utils import logger


class PyPiPackageInspector:
    def __init__(self, tree: str, base_path: str):
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

        Returns:
            dict | None: A dictionary with package name, version, downloads; None if not published.
        """
        package_name = self.get_published_package_name()
        if not package_name:
            return None

        version = self._get_package_version_from_pypi(package_name)
        downloads = self._get_downloads_from_pepy(package_name)

        return {"name": package_name, "version": version, "downloads": downloads}

    def get_published_package_name(self) -> str | None:
        """
        Checks whether a package defined in a file in the repo tree is published on PyPI.

        Returns:
            str | None: The name of the published package, if found and published. Otherwise, None.
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
        Attempts to extract the package name from the contents of pyproject.toml.

        Args:
        content: The content of the pyproject.toml file as a string.

        Returns:
            str | None: The extracted package name if found, otherwise None.
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
        Tries to extract the package name from the contents of setup.py (roughly, via regular expression).

        Args:
            content: The content of the setup.py file as a string.

        Returns:
            str | None: The extracted package name if found, otherwise None.
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

        Args:
            package_name: The name of the package to check.

        Returns:
            bool: True if the package is published on PyPI, False otherwise.
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
        Retrieves version of the package from PyPI.

        Args:
            package_name: The name of the package.

        Returns:
            str | None: A version of the package, or None if request fails.
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
        Retrieves the total downloads count for the package using pepy.tech API.

        Args:
            package_name: The name of the package.

        Returns:
            int | None: The number of downloads or None if request fails.
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
