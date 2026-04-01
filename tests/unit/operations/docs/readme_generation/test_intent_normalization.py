"""Tests for post-parse TaskIntent normalization."""

from osa_tool.operations.docs.readme_generation.agent.models import TaskIntent
from osa_tool.operations.docs.readme_generation.agent.nodes.intent_analyzer import _normalize_task_intent


def test_partial_with_affected_forces_update_task_type() -> None:
    intent = TaskIntent(scope="partial", task_type="improve", affected_sections=["usage"])
    out = _normalize_task_intent(intent)
    assert out.task_type == "update"
    assert out.affected_sections == ["usage"]


def test_full_scope_clears_affected_sections() -> None:
    intent = TaskIntent(scope="full", task_type="improve", affected_sections=["usage"])
    out = _normalize_task_intent(intent)
    assert out.affected_sections == []


def test_partial_without_affected_unchanged() -> None:
    intent = TaskIntent(scope="partial", task_type="improve", affected_sections=[])
    out = _normalize_task_intent(intent)
    assert out.task_type == "improve"
