from enum import Enum
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field

from osa_tool.core.models.event import OperationEvent


class TaskStatus(str, Enum):
    """
    Represents the status of a task within a system.
    
        Class Attributes:
        - PENDING: Indicates the task is waiting to start.
        - IN_PROGRESS: Indicates the task is currently being executed.
        - COMPLETED: Indicates the task has finished successfully.
        - FAILED: Indicates the task has terminated with an error.
    """

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    """
    Represents a task to be executed, tracking its state and results.
    
        Attributes:
            id: Unique identifier for the task.
            description: Human-readable description of the task.
            args: Arguments required for task execution.
            status: Current state of the task (e.g., pending, running, completed).
            result: Output or outcome produced by the task.
            events: Log of significant occurrences during the task lifecycle.
    
        This class encapsulates task metadata and execution state, providing a structured way to manage and monitor asynchronous or background operations.
    """

    id: str
    description: str
    args: Dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    events: List[OperationEvent] = Field(default_factory=list)
