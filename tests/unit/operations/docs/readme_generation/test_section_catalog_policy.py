"""Tests for deterministic section plan policy."""

from osa_tool.operations.docs.readme_generation.agent.models import RepositoryContext, TaskIntent
from osa_tool.operations.docs.readme_generation.agent.section_catalog import deterministic_specs_for_intent


def test_full_intent_includes_all_deterministic_and_toc() -> None:
    specs = deterministic_specs_for_intent(
        TaskIntent(scope="full"),
        RepositoryContext(),
    )
    names = {s.name for s in specs}
    assert "header" in names
    assert "installation" in names
    assert "table_of_contents" in names


def test_partial_with_installation_only() -> None:
    specs = deterministic_specs_for_intent(
        TaskIntent(scope="partial", task_type="update", affected_sections=["installation"]),
        RepositoryContext(),
    )
    names = {s.name for s in specs}
    assert names == {"installation"}


def test_partial_with_only_llm_section_excludes_deterministic() -> None:
    specs = deterministic_specs_for_intent(
        TaskIntent(scope="partial", task_type="update", affected_sections=["usage"]),
        RepositoryContext(),
    )
    assert specs == []


def test_partial_empty_affected_keeps_full_deterministic_fallback() -> None:
    specs = deterministic_specs_for_intent(
        TaskIntent(scope="partial", task_type="update", affected_sections=[]),
        RepositoryContext(),
    )
    names = {s.name for s in specs}
    assert "header" in names
