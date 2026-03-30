"""Deterministic README sections (header, installation, license, etc.) — logic reused by section_generator."""

from __future__ import annotations

import os

import requests
import tomli

from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.logging_utils import summarize_update
from osa_tool.operations.docs.readme_generation.agent.models import SectionResult, SectionSpec
from osa_tool.operations.docs.readme_generation.agent.section_catalog import BUILDER_METHOD_BY_SECTION_NAME
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState
from osa_tool.operations.docs.readme_generation.generator.header import HeaderBuilder
from osa_tool.operations.docs.readme_generation.generator.installation import InstallationSectionBuilder
from osa_tool.operations.docs.readme_generation.models.llm_service import LLMClient
from osa_tool.operations.docs.readme_generation.utils import find_in_repo_tree
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import osa_project_root


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
    """Encapsulates all script-based section builders reused from the original generator module."""

    def __init__(self, context: ReadmeContext) -> None:
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
            pattern = r"\bCITATION(\.\w+)?\b"
            path = self._url_path + self._branch_path + find_in_repo_tree(self._sr.tree, pattern)
            return self._tpl["citation"] + self._tpl["citation_v1"].format(path=path)

        llm_client = LLMClient(self._cm, self._meta)
        citation_from_readme = llm_client.get_citation_from_readme()
        if citation_from_readme:
            return self._tpl["citation"] + citation_from_readme

        return self._tpl["citation"] + self._tpl["citation_v2"].format(
            owner=self._meta.owner,
            year=self._meta.created_at.split("-")[0],
            repo_name=self._cm.get_git_settings().name,
            publisher=self._cm.get_git_settings().host_domain,
            repository_url=self._cm.get_git_settings().repository,
        )

    def table_of_contents(self) -> str:
        return ""


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


def deterministic_builder_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Batch-build deterministic sections (legacy helpers / tests). Prefer section_generator + Send per spec."""
    logger.info("[DeterministicBuilder] Building deterministic sections (batch mode)...")

    specs = [s for s in state.section_plan if s.strategy == "deterministic"]
    if state.current_section is not None and state.current_section.strategy == "deterministic":
        specs = [state.current_section]

    new_sections: dict[str, SectionResult] = {}
    new_errors: dict[str, str] = {}

    for section_spec in specs:
        result, err = build_single_deterministic_section(section_spec, context)
        if err:
            new_errors[section_spec.name] = err
        elif result:
            new_sections[section_spec.name] = result

    update: dict = {"sections": new_sections}
    if new_errors:
        update["section_errors"] = new_errors
    logger.debug("[DeterministicBuilder] Output update summary: %s", summarize_update(update))
    logger.info("[DeterministicBuilder] Done. Built %d deterministic sections.", len(new_sections))
    return update
