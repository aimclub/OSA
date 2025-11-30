from enum import Enum
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field


class AgentStatus(str, Enum):
    INIT = "init"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    WAITING_FOR_USER = "waiting_for_user"
    ERROR = "error"
    DONE = "done"


class OSAAgentState(BaseModel):
    # Input data from the user
    repo_url: Optional[str] = None
    user_request: Optional[str] = None
    attachment: Optional[str] = None

    # System-level metadata
    session_id: str
    step: int = 0
    status: AgentStatus = AgentStatus.INIT

    # Repository metadata / analysis results
    detected_platform: Optional[str] = None
    repo_metadata: Optional[Dict[str, Any]] = None
    source_rank: Optional[Dict[str, Any]] = None

    # Workflow plan and execution state
    tasks: List[str] = Field(default_factory=list)
    current_task_index: Optional[int] = None

    # Conversation and LLM traces
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    llm_trace: List[Dict[str, Any]] = Field(default_factory=list)

    # Additional contextual data
    extra: Dict[str, Any] = Field(default_factory=dict)
