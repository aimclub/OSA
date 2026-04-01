"""README section catalog — derived indexes, planner text, and intent-aware spec selection."""

from osa_tool.operations.docs.readme_generation.agent.models import RepositoryContext, SectionSpec, TaskIntent
from osa_tool.operations.docs.readme_generation.agent.section_catalog_entries import (
    SectionCatalogEntry,
    _SECTION_ENTRIES,
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

# Substrings matched in repo tree + analysis + key files (lowercased).
BENCHMARK_CONTEXT_NEEDLES: tuple[str, ...] = (
    "benchmark",
    "baseline",
    "bleu",
    "map@",
    "wandb",
    "tensorboard",
)

_LLM_ENTRIES_SORTED: tuple[SectionCatalogEntry, ...] = tuple(
    sorted((e for e in _SECTION_ENTRIES if e.strategy == "llm"), key=lambda x: (x.priority, x.name))
)


def format_llm_catalog_for_planner() -> str:
    """Bulleted list of allowed LLM section internal names for the planning prompt."""
    lines = [f"- `{e.name}` — {e.title}: {e.description or 'see catalog'}" for e in _LLM_ENTRIES_SORTED]
    return "\n".join(lines)


def deterministic_specs_for_intent(intent: TaskIntent | None, _ctx: RepositoryContext | None) -> list[SectionSpec]:
    """Deterministic and assembler-only plan slots; filtered on partial updates when ``affected_sections`` is set.

    For partial scope with a non-empty ``affected_sections`` list, only deterministic/catalog
    sections whose internal names appear in that list (case-insensitive) are included. If none match,
    returns an empty list so only LLM sections from the planner run. When ``affected_sections`` is empty
    under partial scope, the full deterministic set is kept (defensive fallback).

    ``_ctx`` is reserved for future conditional rules (e.g. repo signals); currently unused.
    """
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


def _repo_has_paper_signals(intent: TaskIntent | None, ctx: RepositoryContext | None) -> bool:
    return bool(
        (intent and intent.incorporate_paper)
        or (ctx and ctx.pdf_content)
        or (ctx and ctx.article_analysis and ctx.article_analysis.strip() not in ("", "N/A"))
    )


def _repo_has_benchmark_signals(ctx: RepositoryContext | None) -> bool:
    benchmark_blob = (
        f"{ctx.repo_tree if ctx else ''}\n"
        f"{ctx.repo_analysis if ctx and ctx.repo_analysis else ''}\n"
        f"{ctx.key_files_content if ctx and ctx.key_files_content else ''}"
    ).lower()
    return any(needle in benchmark_blob for needle in BENCHMARK_CONTEXT_NEEDLES)


def section_specs_from_llm_names(
    names: list[str], intent: TaskIntent | None, ctx: RepositoryContext | None
) -> list[SectionSpec]:
    """Map planner-selected LLM section names to SectionSpec using catalog metadata (priority, prompts, keys)."""
    has_paper = _repo_has_paper_signals(intent, ctx)
    has_tests = bool(ctx and ctx.has_tests)
    has_benchmark_signal = _repo_has_benchmark_signals(ctx)

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
