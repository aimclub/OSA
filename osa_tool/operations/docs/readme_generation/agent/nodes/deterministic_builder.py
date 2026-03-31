"""Deterministic README sections (header, installation, license, etc.) — logic reused by section_generator."""

from __future__ import annotations

import os

import requests
import tomli

from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.models import SectionResult, SectionSpec
from osa_tool.operations.docs.readme_generation.agent.section_catalog import BUILDER_METHOD_BY_SECTION_NAME
from osa_tool.operations.docs.readme_generation.generator.header import HeaderBuilder
from osa_tool.operations.docs.readme_generation.generator.installation import InstallationSectionBuilder
from osa_tool.operations.docs.readme_generation.utils import find_in_repo_tree
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.utils import extract_readme_content, osa_project_root, parse_folder_name


def _load_template() -> dict:
    path = os.path.join(osa_project_root(), "config", "templates", "template.toml")
    with open(path, "rb") as f:
        return tomli.load(f)


def _check_url(url: str) -> bool:
    try:
        return requests.get(url, timeout=5).status_code == 200
    except Exception:
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
        self._url_path = f"https://{git.host_domain}/{git.full_name}/"
        self._branch_path = f"tree/{self._meta.default_branch}/"

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
        path = self._url_path + self._branch_path + find_in_repo_tree(self._sr.tree, pattern)
        content = self._tpl["examples"].format(path=path)
        logger.info("[DeterministicBuilder] Section 'examples' built from path=%s", path)
        return content

    def documentation(self) -> str:
        logger.info("[DeterministicBuilder] Building section: documentation")
        if not self._meta.homepage_url:
            if self._sr.docs_presence():
                pattern = r"\b(docs?|documentation|wiki|manuals?)\b"
                path = self._url_path + self._branch_path + find_in_repo_tree(self._sr.tree, pattern)
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
        discussions_url = self._url_path + "discussions"
        discussions_enabled = _check_url(discussions_url)
        discussions = self._tpl["discussion_section"].format(discussions_url=discussions_url) if discussions_enabled else ""

        issues_url = self._url_path + "issues"
        issues = self._tpl["issues_section"].format(issues_url=issues_url)

        contributing_text = ""
        has_contributing = self._sr.contributing_presence()
        if has_contributing:
            pattern = r"\b\w*contribut\w*\.(md|rst|txt)$"
            contributing_url = self._url_path + self._branch_path + find_in_repo_tree(self._sr.tree, pattern)
            contributing_text = self._tpl["contributing_section"].format(
                contributing_url=contributing_url, name=self._cm.get_git_settings().name
            )

        content = self._tpl["contributing"].format(
            dicsussion_section=discussions,
            issue_section=issues,
            contributing_section=contributing_text,
        )
        logger.info(
            "[DeterministicBuilder] Section 'contributing' built (discussions=%s, contributing_file=%s)",
            discussions_enabled,
            has_contributing,
        )
        return content

    def license(self) -> str:
        logger.info("[DeterministicBuilder] Building section: license")
        pattern = r"\bLICEN[SC]E(\.\w+)?\b"
        local_license_file = find_in_repo_tree(self._sr.tree, pattern)

        if local_license_file:
            path = self._url_path + self._branch_path + local_license_file
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
            path = self._url_path + self._branch_path + find_in_repo_tree(self._sr.tree, pattern)
            content = self._tpl["citation"] + self._tpl["citation_v1"].format(path=path)
            logger.info("[DeterministicBuilder] Section 'citation' built from repository CITATION file")
            return content

        citation_from_readme = self._extract_citation_from_readme()
        if citation_from_readme:
            content = self._tpl["citation"] + citation_from_readme
            logger.info("[DeterministicBuilder] Section 'citation' built from existing README citation")
            return content

        git = self._cm.get_git_settings()
        content = self._tpl["citation"] + self._tpl["citation_v2"].format(
            owner=self._meta.owner,
            year=self._meta.created_at.split("-")[0],
            repo_name=git.name,
            publisher=git.host_domain,
            repository_url=git.repository,
        )
        logger.info("[DeterministicBuilder] Section 'citation' built from fallback template")
        return content

    def _extract_citation_from_readme(self) -> str:
        """Ask the shared model_handler to find citations in the existing README."""
        logger.info("[DeterministicBuilder] Checking existing README for citation block")
        repo_path = os.path.join(os.getcwd(), parse_folder_name(self._cm.get_git_settings().repository))
        readme_content = extract_readme_content(repo_path)

        logger.info("[DeterministicBuilder] Detecting citations in README via LLM...")
        result = self._context.model_handler.send_and_parse(
            prompt=PromptBuilder.render(self._context.prompts.get("readme.citation"), readme=readme_content),
            parser=LlmTextOutput,
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
