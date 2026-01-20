from osa_tool.osa_agent.base import BaseAgent
from osa_tool.osa_agent.state import OSAState, AgentStatus
from osa_tool.utils.utils import rich_section


class FinalizerAgent(BaseAgent):
    name = "Finalizer"

    def run(self, state: OSAState) -> OSAState:
        rich_section("Finalizer Agent")

        state.active_agent = self.name
        state.status = AgentStatus.COMPLETED

        return state
