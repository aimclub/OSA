from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, ConfigDict

from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.models.agent import AgentStatus
from osa_tool.core.models.task import Task
from osa_tool.tools.repository_analysis.models import RepositoryData


class OSAState(BaseModel):
    # User input
    repo_url: Optional[str] = None
    user_request: Optional[str] = None
    attachment: Optional[str] = None

    # User input memory
    last_attachment: Optional[str] = None

    # Intent
    intent: Optional[str] = None
    task_scope: Optional[str] = None
    intent_confidence: Optional[float] = None

    # Execution metadata
    session_id: str
    step: int = 0
    status: AgentStatus = AgentStatus.INIT
    active_agent: Optional[str] = None

    # Retry loop:
    intent_retry_counter: int = 0

    # Repository
    repo_path: Optional[str] = None
    repo_prepared: bool = False
    repo_data: Optional[RepositoryData] = None
    repo_metadata: Optional[RepositoryMetadata] = None

    # Planning
    plan: List[Task] = Field(default_factory=list)
    current_step_index: Optional[int] = None

    # Artifacts & memory
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    session_memory: List[Dict[str, Any]] = Field(default_factory=list)

    # Review
    approval: bool = False
    delivery_result: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)
