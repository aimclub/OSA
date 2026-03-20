from enum import Enum


class AgentStatus(str, Enum):
    """
    Represents the status of an agent during its execution lifecycle.
    
        Class Attributes:
        - INIT: The initial state when the agent is created.
        - ANALYZING: The state when the agent is analyzing input or context.
        - GENERATING: The state when the agent is generating a response or output.
        - WAITING_FOR_USER: The state when the agent is awaiting user input or feedback.
        - ERROR: The state when an error has occurred during agent execution.
        - COMPLETED: The state when the agent has finished its task successfully.
    
        These class attributes are string constants that define the possible states an agent can be in, used to track and manage the agent's progress and behavior throughout its operation.
    """

    INIT = "init"
    ANALYZING = "analyzing"
    GENERATING = "generating"
    WAITING_FOR_USER = "waiting_for_user"
    ERROR = "error"
    COMPLETED = "completed"
