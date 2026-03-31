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
        return HeaderBuilder(self._cm, self._meta).build_header()

    def installation(self) -> str:
        return InstallationSectionBuilder(self._cm, self._meta).build_installation()

    def examples(self) -> str:
        if not self._sr.examples_presence():
            return ""
        pattern = r"\b(tutorials?|examples|notebooks?)\b"
        path = self._url_path + self._branch_path + find_in_repo_tree(self._sr.tree, pattern)
        return self._tpl["examples"].format(path=path)

    def documentation(self) -> str:
        if not self._meta.homepage_url:
            if self._sr.docs_presence():
                pattern = r"\b(docs?|documentation|wiki|manuals?)\b"
                path = self._url_path + self._branch_path + find_in_repo_tree(self._sr.tree, pattern)
            else:
                return ""
        else:
            path = self._meta.homepage_url
        return self._tpl["documentation"].format(repo_name=self._meta.name, path=path)

    def contributing(self) -> str:
        discussions_url = self._url_path + "discussions"
        discussions = (
            self._tpl["discussion_section"].format(discussions_url=discussions_url)
            if _check_url(discussions_url)
            else ""
        )

        issues_url = self._url_path + "issues"
        issues = self._tpl["issues_section"].format(issues_url=issues_url)

        contributing_text = ""
        if self._sr.contributing_presence():
            pattern = r"\b\w*contribut\w*\.(md|rst|txt)$"
            contributing_url = self._url_path + self._branch_path + find_in_repo_tree(self._sr.tree, pattern)
            contributing_text = self._tpl["contributing_section"].format(
                contributing_url=contributing_url, name=self._cm.get_git_settings().name
            )

        return self._tpl["contributing"].format(
            dicsussion_section=discussions,
            issue_section=issues,
            contributing_section=contributing_text,
        )

    def license(self) -> str:
        if not self._meta.license_name:
            return ""
        pattern = r"\bLICEN[SC]E(\.\w+)?\b"
        help_var = find_in_repo_tree(self._sr.tree, pattern)
        path = self._url_path + self._branch_path + help_var if help_var else self._meta.license_url
        return self._tpl["license"].format(license_name=self._meta.license_name, path=path)

    def citation(self) -> str:
        if self._sr.citation_presence():
            logger.warning("[DeterministicBuilder] Citation file was detected. ")
            pattern = r"\bCITATION(\.\w+)?\b"
            path = self._url_path + self._branch_path + find_in_repo_tree(self._sr.tree, pattern)
            return self._tpl["citation"] + self._tpl["citation_v1"].format(path=path)

        citation_from_readme = self._extract_citation_from_readme()
        if citation_from_readme:
            return self._tpl["citation"] + citation_from_readme

        git = self._cm.get_git_settings()
        return self._tpl["citation"] + self._tpl["citation_v2"].format(
            owner=self._meta.owner,
            year=self._meta.created_at.split("-")[0],
            repo_name=git.name,
            publisher=git.host_domain,
            repository_url=git.repository,
        )

    def _extract_citation_from_readme(self) -> str:
        """Ask the shared model_handler to find citations in the existing README."""
        repo_path = os.path.join(os.getcwd(), parse_folder_name(self._cm.get_git_settings().repository))
        readme_content = extract_readme_content(repo_path)

        logger.info("[DeterministicBuilder] Detecting citations in README...")
        result = self._context.model_handler.send_and_parse(
            prompt=PromptBuilder.render(self._context.prompts.get("readme.citation"), readme=readme_content),
            parser=LlmTextOutput,
        )
        return result.text or ""


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
