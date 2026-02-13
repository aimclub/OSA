from enum import Enum


class AgentStatus(str, Enum):
    INIT = "init"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    WAITING_FOR_USER = "waiting_for_user"
    ERROR = "error"
    COMPLETED = "completed"
