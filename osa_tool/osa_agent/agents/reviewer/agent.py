from osa_tool.osa_agent.base import BaseAgent
from osa_tool.osa_agent.state import OSAState
from osa_tool.utils.utils import rich_section


class ReviewerAgent(BaseAgent):
    name = "Reviewer"

    def run(self, state: OSAState) -> OSAState:
        rich_section("Reviewer Agent")

        state.active_agent = self.name
        state.approval = True

        return state
