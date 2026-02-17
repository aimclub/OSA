from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, Field, ConfigDict

from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.models.agent_status import AgentStatus
from osa_tool.core.models.task import Task
from osa_tool.tools.repository_analysis.models import RepositoryData


class OSAState(BaseModel):
    # User input
    repo_url: Optional[str] = None
    attachment: Optional[str] = None

    # Unified request flow
    active_request: Optional[str] = None
    active_request_source: Optional[Literal["user", "reviewer"]] = None

    # Unified clarification mechanism
    clarification_attempts: int = 3
    clarification_required: bool = False
    clarification_agent: Optional[str] = None
    clarification_type: Literal["single_question", "user_request", "review", "multi_question"] = "single_question"
    clarification_payload: Optional[dict] = None
    clarification_answer: Optional[Any] = None

    # Intent
    intent: Optional[str] = None
    task_scope: Optional[str] = None
    intent_confidence: Optional[float] = None

    # Execution metadata
    session_id: str
    status: AgentStatus = AgentStatus.INIT
    active_agent: Optional[str] = None

    # Repository
    repo_path: Optional[str] = None
    repo_prepared: bool = False
    repo_data: Optional[RepositoryData] = None
    repo_metadata: Optional[RepositoryMetadata] = None

    # Planning
    plan: List[Task] = Field(default_factory=list)
    missing_arguments: list = Field(default_factory=list)
    current_step_index: Optional[int] = None

    # Artifacts & memory
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    session_memory: List[Dict[str, Any]] = Field(default_factory=list)

    # Reviewer feedback
    review_feedback: Optional[str] = None
    review_requires_new_intent: bool = False
    approval: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)
