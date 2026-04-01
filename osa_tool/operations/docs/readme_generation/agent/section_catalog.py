"""Predefined README section catalog — ownership of priority, prompts, context keys, and availability."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from osa_tool.operations.docs.readme_generation.agent.models import RepositoryContext, SectionSpec, TaskIntent

SectionStrategy = Literal["llm", "deterministic", "keep_existing"]


@dataclass(frozen=True)
class SectionCatalogEntry:
    """One known README section and how to generate it."""

    name: str
    title: str
    strategy: SectionStrategy
    priority: int
    description: str = ""
    prompt_context_keys: tuple[str, ...] = ()
    prompt_template_key: str | None = None
    deterministic_builder_method: str | None = None

    def to_section_spec(self) -> SectionSpec:
        return SectionSpec(
            name=self.name,
            title=self.title,
            description=self.description,
            strategy=self.strategy,
            priority=self.priority,
            prompt_context_keys=list(self.prompt_context_keys),
            prompt_template_key=self.prompt_template_key,
        )


_SECTION_ENTRIES: tuple[SectionCatalogEntry, ...] = (
    # deterministic (script-based)
    SectionCatalogEntry(
        name="header",
        title="Header",
        strategy="deterministic",
        priority=0,
        deterministic_builder_method="header",
    ),
    SectionCatalogEntry(
        name="table_of_contents",
        title="Table of Contents",
        strategy="keep_existing",
        priority=5,
        description="Markdown body is synthesized by the assembler from generated section titles; no separate build step.",
    ),
    SectionCatalogEntry(
        name="installation",
        title="Installation",
        strategy="deterministic",
        priority=14,
        deterministic_builder_method="installation",
    ),
    SectionCatalogEntry(
        name="examples",
        title="Examples",
        strategy="deterministic",
        priority=60,
        deterministic_builder_method="examples",
    ),
    SectionCatalogEntry(
        name="documentation",
        title="Documentation",
        strategy="deterministic",
        priority=65,
        deterministic_builder_method="documentation",
    ),
    SectionCatalogEntry(
        name="contributing",
        title="Contributing",
        strategy="deterministic",
        priority=80,
        deterministic_builder_method="contributing",
    ),
    SectionCatalogEntry(
        name="license",
        title="License",
        strategy="deterministic",
        priority=90,
        deterministic_builder_method="license",
    ),
    SectionCatalogEntry(
        name="citation",
        title="Citation",
        strategy="deterministic",
        priority=95,
        deterministic_builder_method="citation",
    ),
    # LLM prose sections (priorities sit between ToC and Installation)
    SectionCatalogEntry(
        name="overview",
        title="Overview",
        strategy="llm",
        priority=10,
        description=(
            "One short paragraph (3–5 sentences): purpose, audience, main entry points "
            "(name actual script/notebook files). No bullet lists; do not enumerate third-party libraries by name."
        ),
        prompt_context_keys=("repo_analysis", "key_files_content", "readme_analysis"),
        prompt_template_key="readme.prompts.section_overview",
    ),
    SectionCatalogEntry(
        name="core_features",
        title="Core Features",
        strategy="llm",
        priority=11,
        description=(
            "3–5 bullets only. Each bullet names a concrete file or function from the repo and one factual sentence. "
            "No bullets about dependencies, stack, type hints, code quality, or generic extensibility."
        ),
        prompt_context_keys=("repo_analysis", "key_files_content"),
        prompt_template_key="readme.prompts.section_core_features",
    ),
    SectionCatalogEntry(
        name="content",
        title="Project structure and components",
        strategy="llm",
        priority=12,
        description=(
            "High-level summary of main components (datasets, modules, notebooks) and how they fit together. "
            "Avoid file-name dump; stay conceptual but grounded in the repo context."
        ),
        prompt_context_keys=("repo_analysis", "key_files_content", "article_analysis"),
        prompt_template_key="readme.prompts.section_content",
    ),
    SectionCatalogEntry(
        name="algorithms",
        title="Methods and algorithms",
        strategy="llm",
        priority=13,
        description=(
            "Summarize main methods or algorithms tied to the paper or codebase. Academic tone; no code dumps; "
            "ground claims in article_analysis and repo context."
        ),
        prompt_context_keys=("repo_analysis", "key_files_content", "article_analysis", "pdf_content"),
        prompt_template_key="readme.prompts.section_algorithms",
    ),
    SectionCatalogEntry(
        name="getting_started",
        title="Getting Started",
        strategy="llm",
        priority=15,
        description=(
            "Minimal steps: env hint, data path from code, run commands copied from the repo. "
            "Do not paste long library lists—refer readers to Installation or requirements."
        ),
        prompt_context_keys=("repo_analysis", "examples_content", "key_files_content"),
        prompt_template_key="readme.prompts.section_getting_started",
    ),
    SectionCatalogEntry(
        name="usage",
        title="Usage",
        strategy="llm",
        priority=16,
        description=(
            "How to invoke the tool or library after install: CLI or API patterns visible in the context. "
            "Do not duplicate Installation; focus on run / import examples."
        ),
        prompt_context_keys=("repo_analysis", "examples_content", "key_files_content"),
        prompt_template_key="readme.prompts.section_usage",
    ),
    SectionCatalogEntry(
        name="architecture",
        title="Architecture",
        strategy="llm",
        priority=17,
        description=(
            "Explain layout and major subsystems when the repo is non-trivial. Use the tree and analysis only; "
            "do not invent components."
        ),
        prompt_context_keys=("repo_tree", "repo_analysis", "key_files_content"),
        prompt_template_key="readme.prompts.section_architecture",
    ),
    SectionCatalogEntry(
        name="api_reference",
        title="API Reference",
        strategy="llm",
        priority=18,
        description=(
            "Document public APIs or stable entry points that appear in key files. Skip if the repo is only scripts "
            "with no clear API."
        ),
        prompt_context_keys=("key_files_content", "repo_analysis"),
        prompt_template_key="readme.prompts.section_api_reference",
    ),
    SectionCatalogEntry(
        name="testing",
        title="Testing",
        strategy="llm",
        priority=19,
        description="How to run tests and what coverage exists, only from context (commands, frameworks, paths).",
        prompt_context_keys=("repo_tree", "repo_analysis", "key_files_content"),
        prompt_template_key="readme.prompts.section_testing",
    ),
    SectionCatalogEntry(
        name="benchmarks",
        title="Benchmarks",
        strategy="llm",
        priority=20,
        description="Reported metrics or benchmark commands only if numbers or benchmark outputs exist in context.",
        prompt_context_keys=("repo_analysis", "key_files_content"),
        prompt_template_key="readme.prompts.section_benchmarks",
    ),
)


SECTION_CATALOG_BY_NAME: dict[str, SectionCatalogEntry] = {e.name: e for e in _SECTION_ENTRIES}

BUILDER_METHOD_BY_SECTION_NAME: dict[str, str] = {
    e.name: (e.deterministic_builder_method or e.name) for e in _SECTION_ENTRIES if e.strategy == "deterministic"
}

DEFAULT_FALLBACK_LLM_SECTION_NAMES: tuple[str, ...] = ("overview", "core_features", "getting_started")
# Present in the plan for ordering; not dispatched to section_generator (see graph fan-out).
_ASSEMBLER_SYNTHESIZED_PLAN_NAMES: frozenset[str] = frozenset({"table_of_contents"})
_PAPER_REQUIRED_SECTIONS: frozenset[str] = frozenset({"content", "algorithms"})
_TEST_REQUIRED_SECTIONS: frozenset[str] = frozenset({"testing"})
_BENCHMARK_RELATED_SECTIONS: frozenset[str] = frozenset({"benchmarks"})


def format_llm_catalog_for_planner() -> str:
    """Bulleted list of allowed LLM section internal names for the planning prompt."""
    lines: list[str] = []
    for e in sorted((x for x in _SECTION_ENTRIES if x.strategy == "llm"), key=lambda x: x.name):
        lines.append(f"- `{e.name}` — {e.title}: {e.description or 'see catalog'}")
    return "\n".join(lines)


def deterministic_specs_for_intent(intent: TaskIntent | None, ctx: RepositoryContext | None) -> list[SectionSpec]:
    """Deterministic and assembler-only plan slots; filtered on partial updates when ``affected_sections`` is set.

    For partial scope with a non-empty ``affected_sections`` list, only deterministic/catalog
    sections whose internal names appear in that list (case-insensitive) are included. If none match,
    returns an empty list so only LLM sections from the planner run. When ``affected_sections`` is empty
    under partial scope, the full deterministic set is kept (defensive fallback).

    ``ctx`` is reserved for future conditional rules (e.g. repo signals); currently unused.
    """
    _ = ctx
    base = [
        e.to_section_spec()
        for e in _SECTION_ENTRIES
        if e.strategy == "deterministic" or e.name in _ASSEMBLER_SYNTHESIZED_PLAN_NAMES
    ]
    if intent is None or intent.scope != "partial":
        return base
    if not intent.affected_sections:
        return base
    want = {s.strip().lower() for s in intent.affected_sections if s and str(s).strip()}
    return [spec for spec in base if spec.name.lower() in want]


def section_specs_from_llm_names(
    names: list[str], intent: TaskIntent | None, ctx: RepositoryContext | None
) -> list[SectionSpec]:
    """Map planner-selected LLM section names to SectionSpec using catalog metadata (priority, prompts, keys)."""
    has_paper = bool(
        (intent and intent.incorporate_paper)
        or (ctx and ctx.pdf_content)
        or (ctx and ctx.article_analysis and ctx.article_analysis.strip() not in ("", "N/A"))
    )
    has_tests = bool(ctx and ctx.has_tests)
    benchmark_blob = (
        f"{ctx.repo_tree if ctx else ''}\n"
        f"{ctx.repo_analysis if ctx and ctx.repo_analysis else ''}\n"
        f"{ctx.key_files_content if ctx and ctx.key_files_content else ''}"
    ).lower()
    has_benchmark_signal = any(
        needle in benchmark_blob
        for needle in ("benchmark", "baseline", " accuracy", "bleu", "map@", "wandb", "tensorboard", "fps ")
    )

    seen: set[str] = set()
    specs: list[SectionSpec] = []
    for n in names:
        if n in seen:
            continue
        seen.add(n)
        entry = SECTION_CATALOG_BY_NAME.get(n)
        if not entry or entry.strategy != "llm":
            continue
        if n in _PAPER_REQUIRED_SECTIONS and not has_paper:
            continue
        if n in _TEST_REQUIRED_SECTIONS and not has_tests:
            continue
        if n in _BENCHMARK_RELATED_SECTIONS and not has_benchmark_signal:
            continue
        specs.append(entry.to_section_spec())
    return specs
