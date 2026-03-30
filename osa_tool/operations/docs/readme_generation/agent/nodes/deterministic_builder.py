"""Generate deterministic README sections (header, installation, license, etc.) without LLM calls."""

from __future__ import annotations

import os

import requests
import tomli

from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.logging_utils import summarize_update
from osa_tool.operations.docs.readme_generation.agent.models import SectionResult, SectionSpec
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

    # ── header ──────────────────────────────────────────────────────────────

    def header(self) -> str:
        return HeaderBuilder(self._cm, self._meta).build_header()

    # ── installation ────────────────────────────────────────────────────────

    def installation(self) -> str:
        return InstallationSectionBuilder(self._cm, self._meta).build_installation()

    # ── examples ────────────────────────────────────────────────────────────

    def examples(self) -> str:
        if not self._sr.examples_presence():
            return ""
        pattern = r"\b(tutorials?|examples|notebooks?)\b"
        path = self._url_path + self._branch_path + find_in_repo_tree(self._sr.tree, pattern)
        return self._tpl["examples"].format(path=path)

    # ── documentation ───────────────────────────────────────────────────────

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

    # ── contributing ────────────────────────────────────────────────────────

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

    # ── license ─────────────────────────────────────────────────────────────

    def license(self) -> str:
        if not self._meta.license_name:
            return ""
        pattern = r"\bLICEN[SC]E(\.\w+)?\b"
        help_var = find_in_repo_tree(self._sr.tree, pattern)
        path = self._url_path + self._branch_path + help_var if help_var else self._meta.license_url
        return self._tpl["license"].format(license_name=self._meta.license_name, path=path)

    # ── citation ────────────────────────────────────────────────────────────

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

    # ── table of contents (generated later by assembler, placeholder here) ──

    def table_of_contents(self) -> str:
        return ""


# ── Node function ───────────────────────────────────────────────────────────

_BUILDER_MAP: dict[str, str] = {
    "header": "header",
    "installation": "installation",
    "examples": "examples",
    "documentation": "documentation",
    "contributing": "contributing",
    "license": "license",
    "citation": "citation",
    "table_of_contents": "table_of_contents",
}


def deterministic_builder_node(state: ReadmeState, context: ReadmeContext) -> dict:
    """Build all deterministic sections from the section plan in a single pass."""
    logger.info("[DeterministicBuilder] Building deterministic sections...")

    spec: SectionSpec | None = state.current_section
    builder = _DeterministicSections(context)

    deterministic_specs = [s for s in state.section_plan if s.strategy == "deterministic"]
    if spec is not None:
        deterministic_specs = [spec]

    new_sections: dict[str, SectionResult] = {}
    new_errors: dict[str, str] = {}

    for section_spec in deterministic_specs:
        method_name = _BUILDER_MAP.get(section_spec.name)
        if method_name is None:
            logger.warning(
                "[DeterministicBuilder] No builder for deterministic section '%s'; skipping.", section_spec.name
            )
            continue

        try:
            content = getattr(builder, method_name)()
        except Exception as exc:
            logger.warning("[DeterministicBuilder] Failed to build '%s': %s", section_spec.name, exc)
            new_errors[section_spec.name] = repr(exc)
            continue

        new_sections[section_spec.name] = SectionResult(
            name=section_spec.name,
            title=section_spec.title,
            content=content,
            source="deterministic",
        )

    update: dict = {"sections": new_sections}
    if new_errors:
        update["section_errors"] = new_errors
    logger.debug("[DeterministicBuilder] Output update summary: %s", summarize_update(update))
    logger.info("[DeterministicBuilder] Done. Built %d deterministic sections.", len(deterministic_specs))
    return update
