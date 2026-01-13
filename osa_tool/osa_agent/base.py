from abc import ABC, abstractmethod

from osa_tool.osa_agent.context import AgentContext
from osa_tool.osa_agent.state import OSAState


class BaseAgent(ABC):
    name: str

    def __init__(self, context: AgentContext):
        self.context = context

    @abstractmethod
    def run(self, state: OSAState) -> OSAState: ...
