"""Generator for codemeta.json — a JSON-LD metadata file following the CodeMeta
standard (https://codemeta.github.io/) for FAIR research-software compliance.

The generator extracts metadata from ``RepositoryMetadata`` and, when available,
from the repository's ``pyproject.toml`` to produce a self-describing
``codemeta.json`` placed at the repository root.
"""

import json
import os
from typing import Any

import tomli

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import resolve_repo_path

# SPDX license mapping for common license names → SPDX URLs
_SPDX_LICENSE_MAP: dict[str, str] = {
    "MIT": "https://spdx.org/licenses/MIT",
    "MIT License": "https://spdx.org/licenses/MIT",
    "Apache-2.0": "https://spdx.org/licenses/Apache-2.0",
    "Apache License 2.0": "https://spdx.org/licenses/Apache-2.0",
    "GPL-3.0": "https://spdx.org/licenses/GPL-3.0-only",
    "GPL-3.0-only": "https://spdx.org/licenses/GPL-3.0-only",
    "GPL-3.0-or-later": "https://spdx.org/licenses/GPL-3.0-or-later",
    "BSD-3-Clause": "https://spdx.org/licenses/BSD-3-Clause",
    "BSD-2-Clause": "https://spdx.org/licenses/BSD-2-Clause",
    "LGPL-3.0": "https://spdx.org/licenses/LGPL-3.0-only",
    "MPL-2.0": "https://spdx.org/licenses/MPL-2.0",
    "ISC": "https://spdx.org/licenses/ISC",
    "Unlicense": "https://spdx.org/licenses/Unlicense",
    "CC0-1.0": "https://spdx.org/licenses/CC0-1.0",
}


class CodeMetaGenerator:
    """Builds a ``codemeta.json`` file from repository metadata.

    The generated file follows the CodeMeta 3.0 JSON-LD context and includes
    the core recommended fields for research software discoverability.
    """

    CODEMETA_CONTEXT = "https://w3id.org/codemeta/3.0"

    def __init__(self, config_manager: ConfigManager, metadata: RepositoryMetadata):
        self.config_manager = config_manager
        self.metadata = metadata
        self.repo_url = str(self.config_manager.get_git_settings().repository)
        self.repo_root = str(resolve_repo_path(self.repo_url))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self) -> str:
        """Generate ``codemeta.json`` and write it to the repository root.

        Returns:
            str: Absolute path to the generated file.
        """
        codemeta = self._build_codemeta()
        output_path = os.path.join(self.repo_root, "codemeta.json")
        with open(output_path, "w", encoding="utf-8") as fh:
            json.dump(codemeta, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        logger.info(f"Generated codemeta.json at {output_path}")
        return output_path

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_codemeta(self) -> dict[str, Any]:
        """Assemble the CodeMeta dictionary from all available sources."""
        pyproject = self._read_pyproject()

        codemeta: dict[str, Any] = {
            "@context": self.CODEMETA_CONTEXT,
            "@type": "SoftwareSourceCode",
            "name": self.metadata.name,
            "description": self._pick_description(pyproject),
        }

        repo_url = self.metadata.clone_url_http or self.metadata.clone_url_ssh
        if repo_url:
            codemeta["codeRepository"] = repo_url

        # License
        license_url = self._resolve_license(pyproject)
        if license_url:
            codemeta["license"] = license_url

        # Version
        version = self._pick_version(pyproject)
        if version:
            codemeta["version"] = version

        # Authors
        authors = self._pick_authors(pyproject)
        if authors:
            codemeta["author"] = authors

        # Programming languages
        if self.metadata.languages:
            codemeta["programmingLanguage"] = self.metadata.languages

        # Dates
        if self.metadata.created_at:
            codemeta["dateCreated"] = self.metadata.created_at
        date_modified = self.metadata.pushed_at or self.metadata.updated_at
        if date_modified:
            codemeta["dateModified"] = date_modified

        # Issue tracker
        if self.metadata.issues_url:
            codemeta["issueTracker"] = self.metadata.issues_url

        # Keywords / topics
        if self.metadata.topics:
            codemeta["keywords"] = self.metadata.topics

        return codemeta

    def _read_pyproject(self) -> dict[str, Any] | None:
        """Try to read ``pyproject.toml`` from the repository root."""
        pyproject_path = os.path.join(self.repo_root, "pyproject.toml")
        if not os.path.isfile(pyproject_path):
            logger.debug("No pyproject.toml found at %s", pyproject_path)
            return None
        try:
            with open(pyproject_path, "rb") as fh:
                return tomli.load(fh)
        except (tomli.TOMLDecodeError, OSError) as exc:
            logger.warning("Failed to parse pyproject.toml: %s", exc)
            return None

    def _pick_description(self, pyproject: dict | None) -> str | None:
        """Return description from metadata, falling back to pyproject."""
        if self.metadata.description:
            return self.metadata.description
        if pyproject:
            return pyproject.get("project", {}).get("description") or pyproject.get("tool", {}).get("poetry", {}).get(
                "description"
            )
        return None

    def _pick_version(self, pyproject: dict | None) -> str | None:
        """Extract version from pyproject.toml."""
        if not pyproject:
            return None
        return pyproject.get("project", {}).get("version") or pyproject.get("tool", {}).get("poetry", {}).get("version")

    def _pick_authors(self, pyproject: dict | None) -> list[dict[str, str]]:
        """Build an ``author`` list from pyproject.toml authors field."""
        if not pyproject:
            return []

        # PEP 621 style: [project].authors = [{name = "...", email = "..."}]
        pep621_authors = pyproject.get("project", {}).get("authors", [])
        if pep621_authors:
            return [self._person_to_codemeta(a) for a in pep621_authors if isinstance(a, dict)]

        # Poetry style: [tool.poetry].authors = ["Name <email>"]
        poetry_authors = pyproject.get("tool", {}).get("poetry", {}).get("authors", [])
        if poetry_authors:
            return [self._parse_poetry_author(a) for a in poetry_authors if isinstance(a, str)]

        return []

    @staticmethod
    def _person_to_codemeta(author: dict[str, str]) -> dict[str, str]:
        """Convert a PEP 621 author dict to CodeMeta Person."""
        person: dict[str, str] = {"@type": "Person"}
        if "name" in author:
            person["name"] = author["name"]
        if "email" in author:
            person["email"] = author["email"]
        return person

    @staticmethod
    def _parse_poetry_author(author_str: str) -> dict[str, str]:
        """Parse a Poetry-style ``'Name <email>'`` string."""
        person: dict[str, str] = {"@type": "Person"}
        if "<" in author_str and ">" in author_str:
            name, rest = author_str.split("<", 1)
            person["name"] = name.strip()
            person["email"] = rest.rstrip(">").strip()
        else:
            person["name"] = author_str.strip()
        return person

    def _resolve_license(self, pyproject: dict | None) -> str | None:
        """Resolve a license name to its SPDX URL."""
        license_name = self.metadata.license_name
        if not license_name and pyproject:
            # PEP 621
            lic = pyproject.get("project", {}).get("license")
            if isinstance(lic, dict):
                license_name = lic.get("text") or lic.get("file")
            elif isinstance(lic, str):
                license_name = lic
            # Poetry fallback
            if not license_name:
                license_name = pyproject.get("tool", {}).get("poetry", {}).get("license")

        if not license_name:
            return None

        return _SPDX_LICENSE_MAP.get(license_name)
