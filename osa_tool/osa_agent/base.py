from abc import ABC, abstractmethod

from osa_tool.osa_agent.context import AgentContext
from osa_tool.osa_agent.state import OSAState


class BaseAgent(ABC):
    """
    Base abstract class for all agents in the OSA workflow.

    Each agent represents a single step in the overall pipeline
    (e.g. intent routing, planning, execution, review, finalization)
    and operates on a shared AgentContext and mutable OSAState.
    """

    name: str

    def __init__(self, context: AgentContext):
        """
        Initialize the agent with a shared execution context.

        Args:
            context (AgentContext): Shared context containing configuration,
                repository metadata, model handlers, and workflow utilities.
        """
        self.context = context

    @abstractmethod
    def run(self, state: OSAState) -> OSAState:
        """
        Execute the agent's logic and return an updated state.

        Args:
            state (OSAState): Current workflow state.

        Returns:
            OSAState: Updated workflow state after agent execution.
        """
        ...
