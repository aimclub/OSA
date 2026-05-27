from osa_tool.core.models.task import Task, TaskStatus
from osa_tool.osa_agent.state import OSAState


def test_osa_state_get_task_finds_by_id():
    # Arrange
    state = OSAState(
        session_id="sid",
        plan=[Task(id="a", description="first"), Task(id="b", description="second")],
    )

    # Act
    found = state.get_task("b")

    # Assert
    assert found is not None
    assert found.id == "b"
    assert found.description == "second"


def test_osa_state_get_task_returns_none_when_missing():
    # Arrange
    state = OSAState(session_id="sid", plan=[])

    # Act
    found = state.get_task("missing")

    # Assert
    assert found is None


def test_osa_state_str_contains_session_and_intent():
    # Arrange
    state = OSAState(session_id="abc", intent="new_task", task_scope="codebase")

    # Act
    text = str(state)

    # Assert
    assert "session_id=abc" in text
    assert "intent=new_task" in text
