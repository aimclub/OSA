"""Static README section definitions: priority, strategy, prompts, and builder wiring."""

from dataclasses import dataclass
from typing import Literal

from osa_tool.operations.docs.readme_generation.agent.models import SectionSpec

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


def _det(
    name: str,
    title: str,
    priority: int,
    *,
    builder: str | None = None,
    description: str = "",
) -> SectionCatalogEntry:
    return SectionCatalogEntry(
        name=name,
        title=title,
        strategy="deterministic",
        priority=priority,
        description=description,
        deterministic_builder_method=builder or name,
    )


_SECTION_ENTRIES: tuple[SectionCatalogEntry, ...] = (
    _det("header", "Header", 0),
    SectionCatalogEntry(
        name="table_of_contents",
        title="Table of Contents",
        strategy="keep_existing",
        priority=5,
        description="Markdown body is synthesized by the assembler from generated section titles; no separate build step.",
    ),
    _det("installation", "Installation", 14),
    _det("examples", "Examples", 60),
    _det("documentation", "Documentation", 65),
    _det("contributing", "Contributing", 80),
    _det("license", "License", 90),
    _det("citation", "Citation", 95),
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
