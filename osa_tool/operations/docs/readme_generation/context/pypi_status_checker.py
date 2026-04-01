"""Inspect PyPI for package metadata (name, version, downloads)."""

import os
import re

import requests
import tomli

from osa_tool.operations.docs.readme_generation.utils import find_in_repo_tree, read_file
from osa_tool.utils.logger import logger


class PyPiPackageInspector:
    """Detect whether a project is published on PyPI and gather basic metadata."""

    _PYPI_URL = "https://pypi.org/pypi/{package}/json"
    _PEPY_URL = "https://api.pepy.tech/api/v2/projects/{package}"
    _FILE_PATTERNS = (r"pyproject\.toml", r"setup\.py")
    _HTTP_TIMEOUT = 10
    _SETUP_NAME_RE = re.compile(r"(?i)(?:^|\s)name\s*=\s*['\"]([^'\"]+)['\"]")

    def __init__(self, tree: str, base_path: str) -> None:
        self.tree = tree
        self.base_path = base_path
        self._api_key = os.getenv("X-API-Key")
        logger.debug("[PyPiInspector] Initialized (base_path=%s, has_api_key=%s)", self.base_path, bool(self._api_key))

    def get_info(self) -> dict[str, str | int | None] | None:
        """Return ``{name, version, downloads}`` if published on PyPI, else ``None``."""
        logger.info("[PyPiInspector] Resolving PyPI package info")
        package_name = self.get_published_package_name()
        if not package_name:
            logger.info("[PyPiInspector] Published package not found")
            return None

        version = self._get_package_version_from_pypi(package_name)
        downloads = self._get_downloads_from_pepy(package_name)
        info = {"name": package_name, "version": version, "downloads": downloads}
        logger.info(
            "[PyPiInspector] Resolved package info: name=%s, version=%s, downloads=%s",
            package_name,
            version,
            downloads,
        )
        return info

    def get_published_package_name(self) -> str | None:
        """Search repo files for a package name that is actually on PyPI."""
        logger.debug("[PyPiInspector] Looking for package name in repository metadata files")
        for pattern in self._FILE_PATTERNS:
            filename = find_in_repo_tree(self.tree, pattern)
            if not filename:
                logger.debug("[PyPiInspector] No file matching pattern '%s'", pattern)
                continue

            file_path = os.path.join(self.base_path, filename)
            logger.debug("[PyPiInspector] Reading candidate metadata file: %s", file_path)
            content = read_file(file_path)
            if not content.strip():
                continue

            name: str | None = None
            if file_path.endswith("pyproject.toml"):
                name = self._extract_package_name_from_pyproject(content)
            elif file_path.endswith("setup.py"):
                name = self._extract_package_name_from_setup(content)

            logger.debug("[PyPiInspector] Candidate package from %s: %s", filename, name)
            if name and self._is_published_on_pypi(name):
                logger.info("[PyPiInspector] Found published package: %s", name)
                return name

        logger.debug("[PyPiInspector] No published package name detected")
        return None

    @staticmethod
    def _extract_package_name_from_pyproject(content: str) -> str | None:
        """Extract package name from pyproject.toml (PEP 621 or Poetry style)."""
        try:
            data = tomli.loads(content)
        except tomli.TOMLDecodeError:
            logger.error("[PyPiInspector] Failed to decode pyproject.toml")
            return None
        name = data.get("project", {}).get("name") or data.get("tool", {}).get("poetry", {}).get("name")
        logger.debug("[PyPiInspector] Parsed package name from pyproject.toml: %s", name)
        return name

    def _extract_package_name_from_setup(self, content: str) -> str | None:
        """Extract package name from setup.py via regex."""
        match = self._SETUP_NAME_RE.search(content)
        name = match.group(1) if match else None
        logger.debug("[PyPiInspector] Parsed package name from setup.py: %s", name)
        return name

    def _is_published_on_pypi(self, package_name: str) -> bool:
        """Check if *package_name* exists on PyPI."""
        url = self._PYPI_URL.format(package=package_name)
        try:
            status_code = requests.get(url, timeout=self._HTTP_TIMEOUT).status_code
            is_published = status_code == 200
            logger.debug("[PyPiInspector] PyPI check for %s -> status=%s", package_name, status_code)
            return is_published
        except requests.RequestException:
            logger.error("[PyPiInspector] PyPI reachability check failed for %s", package_name, exc_info=True)
            return False

    def _get_package_version_from_pypi(self, package_name: str) -> str | None:
        """Fetch the latest version string from PyPI."""
        url = self._PYPI_URL.format(package=package_name)
        try:
            resp = requests.get(url, timeout=self._HTTP_TIMEOUT)
            if resp.status_code == 200:
                version = resp.json().get("info", {}).get("version")
                logger.debug("[PyPiInspector] Latest PyPI version for %s: %s", package_name, version)
                return version
            logger.warning(
                "[PyPiInspector] PyPI version request returned status=%s for %s", resp.status_code, package_name
            )
        except requests.RequestException:
            logger.error("[PyPiInspector] Failed to fetch version from PyPI for %s", package_name, exc_info=True)
        return None

    def _get_downloads_from_pepy(self, package_name: str) -> int | None:
        """Fetch total download count from pepy.tech."""
        url = self._PEPY_URL.format(package=package_name)
        headers = {"X-API-Key": self._api_key} if self._api_key else {}
        try:
            resp = requests.get(url, headers=headers, timeout=self._HTTP_TIMEOUT)
            if resp.status_code == 200:
                downloads = resp.json().get("total_downloads")
                logger.debug("[PyPiInspector] pepy downloads for %s: %s", package_name, downloads)
                return downloads
            logger.error("[PyPiInspector] Pepy request failed for %s (status %d)", package_name, resp.status_code)
        except requests.RequestException:
            logger.error("[PyPiInspector] Failed to fetch downloads from pepy.tech for %s", package_name, exc_info=True)
        return None
