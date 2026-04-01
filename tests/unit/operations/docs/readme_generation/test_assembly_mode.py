"""Tests for README assembly mode selection."""

from osa_tool.operations.docs.readme_generation.agent.models import RepositoryContext, TaskIntent
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState


def _state(**kwargs) -> ReadmeState:
    return ReadmeState(repo_url="https://example.com/o/r", **kwargs)


def test_merge_existing_when_partial_and_real_readme() -> None:
    state = _state(
        intent=TaskIntent(scope="partial", task_type="improve", affected_sections=["usage"]),
        context=RepositoryContext(existing_readme="# Title\n\nHello"),
    )
    assert state.readme_assembly_mode() == "merge_existing"


def test_full_compose_when_partial_but_empty_readme() -> None:
    state = _state(
        intent=TaskIntent(scope="partial"),
        context=RepositoryContext(existing_readme=""),
    )
    assert state.readme_assembly_mode() == "full_compose"


def test_full_compose_when_full_scope_even_with_readme() -> None:
    state = _state(
        intent=TaskIntent(scope="full"),
        context=RepositoryContext(existing_readme="# Hi"),
    )
    assert state.readme_assembly_mode() == "full_compose"
