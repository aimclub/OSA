import pytest

from osa_tool.operations.registry import Operation, OperationRegistry
from osa_tool.osa_agent.state import OSAState


class _DummyOperation(Operation):
    name = "dummy_test_op"
    description = "test"
    supported_intents = ["new_task"]
    supported_scopes = ["full_repo"]


@pytest.fixture
def isolated_registry():
    # Arrange
    saved = OperationRegistry._operations.copy()
    OperationRegistry._operations.clear()
    yield
    OperationRegistry._operations.clear()
    OperationRegistry._operations.update(saved)


def test_operation_registry_register_and_get(isolated_registry):
    # Arrange
    op = _DummyOperation()

    # Act
    OperationRegistry.register(op)

    # Assert
    assert OperationRegistry.get("dummy_test_op") is op


def test_operation_is_applicable_respects_intent(isolated_registry):
    # Arrange
    OperationRegistry.register(_DummyOperation())
    op = OperationRegistry.get("dummy_test_op")
    state = OSAState(session_id="s1", intent="other", task_scope="full_repo")

    # Act
    ok = op.is_applicable(state)

    # Assert
    assert ok is False


def test_operation_is_applicable_when_matching(isolated_registry):
    # Arrange
    OperationRegistry.register(_DummyOperation())
    op = OperationRegistry.get("dummy_test_op")
    state = OSAState(session_id="s1", intent="new_task", task_scope="full_repo")

    # Act
    ok = op.is_applicable(state)

    # Assert
    assert ok is True


def test_operation_plan_tasks_returns_single_task(isolated_registry):
    # Arrange
    op = _DummyOperation()

    # Act
    tasks = op.plan_tasks()

    # Assert
    assert len(tasks) == 1
    assert tasks[0].id == "dummy_test_op"
    assert tasks[0].description == "test"


def test_get_execution_descriptor_unknown_operation_raises(isolated_registry):
    with pytest.raises(ValueError, match="Unknown operation"):
        OperationRegistry.get_execution_descriptor("missing_op")
