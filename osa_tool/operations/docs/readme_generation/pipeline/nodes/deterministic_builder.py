"""Deterministic README sections (header, installation, license, etc.) — logic reused by section_generator."""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
import tomli

from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.operations.docs.readme_generation.pipeline.runtime_context import ReadmeContext
from osa_tool.operations.docs.readme_generation.pipeline.models import SectionResult, SectionSpec
from osa_tool.operations.docs.readme_generation.pipeline.section_catalog import BUILDER_METHOD_BY_SECTION_NAME
from osa_tool.operations.docs.readme_generation.sections.header import HeaderBuilder
from osa_tool.operations.docs.readme_generation.sections.installation import InstallationSectionBuilder
from osa_tool.operations.docs.readme_generation.readme_utils import (
    build_system_message,
    find_in_repo_tree,
    resolve_repo_host_and_root_url,
    to_readme_relative_link,
)
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.utils import extract_readme_content, osa_project_root, resolve_repo_path


def _load_template() -> dict[str, Any]:
    path = os.path.join(osa_project_root(), "config", "templates", "template.toml")
    with open(path, "rb") as f:
        return tomli.load(f)


def _check_url(url: str) -> bool:
    try:
        return requests.get(url, timeout=5).status_code == 200
    except requests.RequestException:
        return False


class _DeterministicSections:
    """Script-based section builders that don't require LLM prose generation."""

    def __init__(self, context: ReadmeContext) -> None:
        self._context = context
        self._cm = context.config_manager
        self._meta = context.metadata
        self._sr = SourceRank(self._cm)
        self._tpl = _load_template()

        git = self._cm.get_git_settings()
        self._host, self._repo_root_url = resolve_repo_host_and_root_url(
            repo_url=git.repository,
            clone_url_http=self._meta.clone_url_http,
            host=git.host,
            host_domain=git.host_domain,
            full_name=git.full_name,
        )
        self._is_local_repo = Path(git.repository).expanduser().is_dir()

    def _local_repo_link(self, pattern: str, *, prefer_directory: bool = False) -> str:
        rel_path = find_in_repo_tree(self._sr.tree, pattern, prefer_directory=prefer_directory)
        return to_readme_relative_link(rel_path)

    def _issues_link(self) -> str:
        if self._meta.issues_url:
            return self._meta.issues_url.split("{", 1)[0]
        if self._repo_root_url != ".":
            suffix = "tasktracker" if self._host == "gitverse" else "issues"
            return f"{self._repo_root_url}{suffix}"
        pattern = r"\bBUG_ISSUE\.(md|rst|txt)$"
        return self._local_repo_link(pattern)

    def _contributing_link(self) -> str:
        pattern = r"\b\w*contribut\w*\.(md|rst|txt)$"
        return self._local_repo_link(pattern)

    def _citation_repository_reference(self) -> str:
        if self._meta.clone_url_http:
            return self._meta.clone_url_http.removesuffix(".git")
        if self._repo_root_url != ".":
            return self._repo_root_url.rstrip("/")
        return "REPOSITORY_URL"

    def header(self) -> str:
        logger.info("[DeterministicBuilder] Building section: header")
        content = HeaderBuilder(self._cm, self._meta).build_header()
        logger.info("[DeterministicBuilder] Section 'header' built (%d chars)", len(content))
        return content

    def installation(self) -> str:
        logger.info("[DeterministicBuilder] Building section: installation")
        content = InstallationSectionBuilder(self._cm, self._meta).build_installation()
        logger.info("[DeterministicBuilder] Section 'installation' built (%d chars)", len(content))
        return content

    def examples(self) -> str:
        logger.info("[DeterministicBuilder] Building section: examples")
        if not self._sr.examples_presence():
            logger.info("[DeterministicBuilder] Section 'examples' skipped: no examples detected")
            return ""
        pattern = r"\b(tutorials?|examples|notebooks?)\b"
        path = self._local_repo_link(pattern, prefer_directory=True)
        content = self._tpl["examples"].format(path=path)
        logger.info("[DeterministicBuilder] Section 'examples' built from path=%s", path)
        return content

    def documentation(self) -> str:
        logger.info("[DeterministicBuilder] Building section: documentation")
        if not self._meta.homepage_url:
            if self._sr.docs_presence():
                pattern = r"\b(docs?|documentation|wiki|manuals?)\b"
                path = self._local_repo_link(pattern, prefer_directory=True)
            else:
                logger.info("[DeterministicBuilder] Section 'documentation' skipped: docs not found")
                return ""
        else:
            path = self._meta.homepage_url
        content = self._tpl["documentation"].format(repo_name=self._meta.name, path=path)
        logger.info("[DeterministicBuilder] Section 'documentation' built with path=%s", path)
        return content

    def contributing(self) -> str:
        logger.info("[DeterministicBuilder] Building section: contributing")
        discussions_url = f"{self._repo_root_url}discussions" if self._repo_root_url != "." else "."
        discussions_enabled = discussions_url != "." and _check_url(discussions_url)
        discussions = (
            self._tpl["discussion_section"].format(discussions_url=discussions_url) if discussions_enabled else ""
        )

        issues_url = self._issues_link()
        issues = self._tpl["issues_section"].format(issues_url=issues_url) if issues_url else ""

        contributing_url = self._contributing_link() if self._sr.contributing_presence() else ""
        contributing_text = (
            self._tpl["contributing_section"].format(
                contributing_url=contributing_url, name=self._cm.get_git_settings().name
            )
            if contributing_url
            else ""
        )

        content = self._tpl["contributing"].format(
            dicsussion_section=discussions,
            issue_section=issues,
            contributing_section=contributing_text,
        )
        logger.info(
            "[DeterministicBuilder] Section 'contributing' built (discussions=%s, contributing_file=%s)",
            discussions_enabled,
            bool(contributing_url),
        )
        return content

    def license(self) -> str:
        logger.info("[DeterministicBuilder] Building section: license")
        pattern = r"\bLICEN[SC]E(\.\w+)?\b"
        local_license_file = find_in_repo_tree(self._sr.tree, pattern)

        if local_license_file:
            path = to_readme_relative_link(local_license_file)
            license_name = self._meta.license_name or "License"
            content = self._tpl["license"].format(license_name=license_name, path=path)
            logger.info(
                "[DeterministicBuilder] Section 'license' built from local file=%s (license_name=%s)",
                local_license_file,
                license_name,
            )
            return content

        if not self._meta.license_name or not self._meta.license_url:
            logger.info(
                "[DeterministicBuilder] Section 'license' skipped: no local LICENSE file and no complete license metadata"
            )
            return ""

        path = self._meta.license_url
        content = self._tpl["license"].format(license_name=self._meta.license_name, path=path)
        logger.info("[DeterministicBuilder] Section 'license' built with path=%s", path)
        return content

    def citation(self) -> str:
        logger.info("[DeterministicBuilder] Building section: citation")
        if self._sr.citation_presence():
            logger.info("[DeterministicBuilder] Citation file detected in repository")
            pattern = r"\bCITATION(\.\w+)?\b"
            path = self._local_repo_link(pattern)
            content = self._tpl["citation"] + self._tpl["citation_v1"].format(path=path)
            logger.info("[DeterministicBuilder] Section 'citation' built from repository CITATION file")
            return content

        citation_from_readme = self._extract_citation_from_readme()
        if citation_from_readme:
            content = self._tpl["citation"] + citation_from_readme
            logger.info("[DeterministicBuilder] Section 'citation' built from existing README citation")
            return content

        git = self._cm.get_git_settings()
        year = self._meta.created_at.split("-")[0] if self._meta.created_at else str(datetime.now().year)
        repository_reference = self._citation_repository_reference()
        if self._is_local_repo and not self._meta.clone_url_http:
            content = self._tpl["citation"] + self._tpl["citation_v3"].format(
                owner=self._meta.owner or "",
                year=year,
                repo_name=git.name,
                repository_hint=repository_reference,
            )
            logger.info("[DeterministicBuilder] Section 'citation' built from local fallback template")
            return content
        content = self._tpl["citation"] + self._tpl["citation_v2"].format(
            owner=self._meta.owner or "",
            year=year,
            repo_name=git.name,
            publisher=git.host_domain or "Repository host",
            repository_url=repository_reference,
        )
        logger.info("[DeterministicBuilder] Section 'citation' built from fallback template")
        return content

    def _extract_citation_from_readme(self) -> str:
        """Ask the shared model_handler to find citations in the existing README."""
        logger.info("[DeterministicBuilder] Checking existing README for citation block")
        repo_path = str(resolve_repo_path(self._cm.get_git_settings().repository))
        readme_content = extract_readme_content(repo_path)

        logger.info("[DeterministicBuilder] Detecting citations in README via LLM...")
        result = self._context.model_handler.send_and_parse(
            prompt=PromptBuilder.render(self._context.prompts.get("readme.prompts.citation"), readme=readme_content),
            parser=LlmTextOutput,
            system_message=build_system_message(self._context, "repo_analysis"),
        )
        detected = result.text or ""
        logger.info("[DeterministicBuilder] Citation detection complete (found=%s)", bool(detected.strip()))
        return detected


def build_single_deterministic_section(
    spec: SectionSpec,
    context: ReadmeContext,
) -> tuple[SectionResult | None, str | None]:
    """Build one deterministic section. On failure returns (None, error_repr)."""
    method_name = BUILDER_METHOD_BY_SECTION_NAME.get(spec.name)
    if method_name is None:
        logger.warning("[DeterministicBuilder] No builder for section '%s'; skipping.", spec.name)
        return None, None

    builder = _DeterministicSections(context)
    try:
        content = getattr(builder, method_name)()
    except Exception as exc:
        logger.warning("[DeterministicBuilder] Failed to build '%s': %s", spec.name, exc)
        return None, repr(exc)

    return (
        SectionResult(
            name=spec.name,
            title=spec.title,
            content=content,
            source="deterministic",
        ),
        None,
    )
