from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.core.models.task import Task, TaskStatus


def test_task_default_status_and_collections():
    # Act
    task = Task(id="op1", description="Do work")

    # Assert
    assert task.status == TaskStatus.PENDING
    assert task.args == {}
    assert task.result is None
    assert task.events == []


def test_task_with_events():
    # Arrange
    ev = OperationEvent(kind=EventKind.CREATED, target="README.md", data={})

    # Act
    task = Task(id="readme", description="gen", events=[ev])

    # Assert
    assert len(task.events) == 1
    assert task.events[0].kind == EventKind.CREATED
