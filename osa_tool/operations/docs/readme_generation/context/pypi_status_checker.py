"""Inspect PyPI for package metadata (name, version, downloads)."""

from __future__ import annotations

import os
import re

import requests
import tomli

from osa_tool.operations.docs.readme_generation.utils import find_in_repo_tree, read_file
from osa_tool.utils.logger import logger

_HTTP_TIMEOUT = 10
_SETUP_NAME_RE = re.compile(r"(?i)(?:^|\s)name\s*=\s*['\"]([^'\"]+)['\"]")


class PyPiPackageInspector:
    """Detect whether a project is published on PyPI and gather basic metadata."""

    _PYPI_URL = "https://pypi.org/pypi/{package}/json"
    _PEPY_URL = "https://api.pepy.tech/api/v2/projects/{package}"
    _FILE_PATTERNS = (r"pyproject\.toml", r"setup\.py")

    def __init__(self, tree: str, base_path: str) -> None:
        self.tree = tree
        self.base_path = base_path
        self._api_key = os.getenv("X-API-Key")

    def get_info(self) -> dict[str, str | int | None] | None:
        """Return ``{name, version, downloads}`` if published on PyPI, else ``None``."""
        package_name = self.get_published_package_name()
        if not package_name:
            return None

        version = self._get_package_version_from_pypi(package_name)
        downloads = self._get_downloads_from_pepy(package_name)
        return {"name": package_name, "version": version, "downloads": downloads}

    # ------------------------------------------------------------------
    # Package-name discovery
    # ------------------------------------------------------------------

    def get_published_package_name(self) -> str | None:
        """Search repo files for a package name that is actually on PyPI."""
        for pattern in self._FILE_PATTERNS:
            filename = find_in_repo_tree(self.tree, pattern)
            if not filename:
                continue

            file_path = os.path.join(self.base_path, filename)
            try:
                content = read_file(file_path)
            except Exception:
                logger.error("Error reading %s", file_path, exc_info=True)
                continue

            name: str | None = None
            if file_path.endswith("pyproject.toml"):
                name = self._extract_package_name_from_pyproject(content)
            elif file_path.endswith("setup.py"):
                name = self._extract_package_name_from_setup(content)

            if name and self._is_published_on_pypi(name):
                return name

        return None

    @staticmethod
    def _extract_package_name_from_pyproject(content: str) -> str | None:
        """Extract package name from pyproject.toml (PEP 621 or Poetry style)."""
        try:
            data = tomli.loads(content)
        except tomli.TOMLDecodeError:
            logger.error("Failed to decode pyproject.toml")
            return None
        return data.get("project", {}).get("name") or data.get("tool", {}).get("poetry", {}).get("name")

    def _extract_package_name_from_setup(self, content: str) -> str | None:
        """Extract package name from setup.py via regex."""
        match = _SETUP_NAME_RE.search(content)
        return match.group(1) if match else None

    # ------------------------------------------------------------------
    # PyPI / pepy HTTP helpers
    # ------------------------------------------------------------------

    def _is_published_on_pypi(self, package_name: str) -> bool:
        """Check if *package_name* exists on PyPI."""
        url = self._PYPI_URL.format(package=package_name)
        try:
            return requests.get(url, timeout=_HTTP_TIMEOUT).status_code == 200
        except requests.RequestException:
            logger.error("PyPI reachability check failed for %s", package_name, exc_info=True)
            return False

    def _get_package_version_from_pypi(self, package_name: str) -> str | None:
        """Fetch the latest version string from PyPI."""
        url = self._PYPI_URL.format(package=package_name)
        try:
            resp = requests.get(url, timeout=_HTTP_TIMEOUT)
            if resp.status_code == 200:
                return resp.json().get("info", {}).get("version")
        except requests.RequestException:
            logger.error("Failed to fetch version from PyPI for %s", package_name, exc_info=True)
        return None

    def _get_downloads_from_pepy(self, package_name: str) -> int | None:
        """Fetch total download count from pepy.tech."""
        url = self._PEPY_URL.format(package=package_name)
        headers = {"X-API-Key": self._api_key} if self._api_key else {}
        try:
            resp = requests.get(url, headers=headers, timeout=_HTTP_TIMEOUT)
            if resp.status_code == 200:
                return resp.json().get("total_downloads")
            logger.error("Pepy request failed for %s (status %d)", package_name, resp.status_code)
        except requests.RequestException:
            logger.error("Failed to fetch downloads from pepy.tech for %s", package_name, exc_info=True)
        return None
