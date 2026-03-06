from enum import Enum
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, Field

from osa_tool.core.models.event import OperationEvent


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: str
    description: str
    args: Dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    events: List[OperationEvent] = Field(default_factory=list)
