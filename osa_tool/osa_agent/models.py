from enum import Enum
from typing import Optional, Literal, Dict, Any, List

from pydantic import BaseModel


class IntentDecision(BaseModel):
    """
    Output of IntentRouter agent.
    """

    intent: Literal["new_task", "feedback", "unknown"]
    task_scope: Optional[
        Literal[
            "none",
            "analysis",  # only analysis, reports
            "docs",  # documentation (README, LICENSE, community, about)
            "codebase",  # code + structure + files
            "full_repo",  # all
        ]
    ] = None
    confidence: float


class PlannerDecision(BaseModel):
    """
    Output of Planner agent.
    """

    operations: List[str]
    reasoning: str


class AgentStatus(str, Enum):
    INIT = "init"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    WAITING_FOR_USER = "waiting_for_user"
    ERROR = "error"
    DONE = "done"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    id: str
    description: str

    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
