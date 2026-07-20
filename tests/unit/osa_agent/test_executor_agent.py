from unittest.mock import MagicMock

import pytest

from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.core.models.task import Task, TaskStatus
from osa_tool.operations.registry import Operation, OperationRegistry
from osa_tool.osa_agent.agents.executor.agent import ExecutorAgent
from osa_tool.osa_agent.state import OSAState


class _TestOperation(Operation):
    name = "executor_test_op"
    description = "test"
    supported_intents = ["new_task"]
    supported_scopes = ["full_repo"]
    executor = None


@pytest.fixture
def isolated_registry():
    saved = OperationRegistry._operations.copy()
    OperationRegistry._operations.clear()
    yield
    OperationRegistry._operations.clear()
    OperationRegistry._operations.update(saved)


@pytest.fixture
def executor():
    return ExecutorAgent(context=MagicMock())


@pytest.mark.parametrize(
    ("normalized", "expected"),
    [
        ({"result": {"error": "boom"}, "events": []}, True),
        (
            {
                "result": None,
                "events": [OperationEvent(kind=EventKind.FAILED, target="README.md")],
            },
            True,
        ),
        (
            {
                "result": {"file": "README.md"},
                "events": [OperationEvent(kind=EventKind.GENERATED, target="README.md")],
            },
            False,
        ),
        (
            {
                "result": {"generated": False},
                "events": [OperationEvent(kind=EventKind.SKIPPED, target="workflows")],
            },
            False,
        ),
        (
            {
                "result": {"generated": False},
                "events": [OperationEvent(kind=EventKind.FAILED, target="workflows")],
            },
            True,
        ),
        (
            {
                "result": {"path": "requirements.txt"},
                "events": [
                    OperationEvent(kind=EventKind.FAILED, target="requirements.txt", data={"mode": "scan-notebooks"}),
                    OperationEvent(kind=EventKind.GENERATED, target="requirements.txt", data={"mode": "no-notebooks"}),
                ],
            },
            False,
        ),
        (
            {
                "result": {"generated": ["CONTRIBUTING.md"]},
                "events": [
                    OperationEvent(kind=EventKind.FAILED, target="SECURITY"),
                    OperationEvent(kind=EventKind.GENERATED, target="CONTRIBUTING"),
                ],
            },
            False,
        ),
    ],
)
def test_is_failure_result(executor, normalized, expected):
    assert executor._is_failure_result(normalized) is expected


def test_run_task_marks_failed_when_operation_reports_failure(isolated_registry, executor):
    def failing_executor():
        return {
            "result": None,
            "events": [OperationEvent(kind=EventKind.FAILED, target="README.md", data={"error": "timeout"})],
        }

    op = _TestOperation()
    op.executor = failing_executor
    OperationRegistry.register(op)

    task = Task(id="executor_test_op", description="test")
    state = OSAState(session_id="s1")

    executor._run_task(task, state)

    assert task.status is TaskStatus.FAILED
    assert task.result is None
    assert len(task.events) == 1


def test_run_task_marks_completed_on_success(isolated_registry, executor):
    def successful_executor():
        return {
            "result": {"file": "README.md"},
            "events": [OperationEvent(kind=EventKind.GENERATED, target="README.md")],
        }

    op = _TestOperation()
    op.executor = successful_executor
    OperationRegistry.register(op)

    task = Task(id="executor_test_op", description="test")
    state = OSAState(session_id="s1")

    executor._run_task(task, state)

    assert task.status is TaskStatus.COMPLETED
    assert task.result == {"file": "README.md"}


def test_run_task_marks_failed_on_exception(isolated_registry, executor):
    def raising_executor():
        raise RuntimeError("unexpected crash")

    op = _TestOperation()
    op.executor = raising_executor
    OperationRegistry.register(op)

    task = Task(id="executor_test_op", description="test")
    state = OSAState(session_id="s1")

    executor._run_task(task, state)

    assert task.status is TaskStatus.FAILED
    assert task.result == {"error": "unexpected crash"}
