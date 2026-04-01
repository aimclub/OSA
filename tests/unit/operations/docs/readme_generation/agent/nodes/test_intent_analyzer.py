from osa_tool.operations.docs.readme_generation.agent.models import TaskIntent
from osa_tool.operations.docs.readme_generation.agent.nodes.intent_analyzer import _normalize_task_intent


def test_normalize_task_intent_forces_update_for_partial_with_affected_sections() -> None:
    # Arrange
    intent = TaskIntent(scope="partial", task_type="improve", affected_sections=["usage"])

    # Act
    normalized = _normalize_task_intent(intent)

    # Assert
    assert normalized.task_type == "update"
    assert normalized.affected_sections == ["usage"]


def test_normalize_task_intent_clears_affected_sections_for_full_scope() -> None:
    # Arrange
    intent = TaskIntent(scope="full", task_type="improve", affected_sections=["usage"])

    # Act
    normalized = _normalize_task_intent(intent)

    # Assert
    assert normalized.affected_sections == []


def test_normalize_task_intent_keeps_partial_without_affected_sections() -> None:
    # Arrange
    intent = TaskIntent(scope="partial", task_type="improve", affected_sections=[])

    # Act
    normalized = _normalize_task_intent(intent)

    # Assert
    assert normalized.task_type == "improve"
