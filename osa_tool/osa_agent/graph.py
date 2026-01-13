from langgraph.constants import END
from langgraph.graph import StateGraph

from osa_tool.core.models.agent import AgentStatus
from osa_tool.osa_agent.agents.executor.agent import ExecutorAgent
from osa_tool.osa_agent.agents.finalizer.agent import FinalizerAgent
from osa_tool.osa_agent.agents.intent_router.agent import IntentRouterAgent
from osa_tool.osa_agent.agents.planner.agent import PlannerAgent
from osa_tool.osa_agent.agents.repo_analysis.agent import RepoAnalysisAgent
from osa_tool.osa_agent.agents.reviewer.agent import ReviewerAgent
from osa_tool.osa_agent.context import AgentContext
from osa_tool.osa_agent.state import OSAState


def build_graph(context: AgentContext):
    # instantiate agents
    intent_router = IntentRouterAgent(context)
    repo_analysis = RepoAnalysisAgent(context)
    planner = PlannerAgent(context)
    executor = ExecutorAgent(context)
    reviewer = ReviewerAgent(context)
    finalizer = FinalizerAgent(context)

    graph = StateGraph(OSAState)

    graph.add_node("intent_router", intent_router.run)
    graph.add_node("repo_analysis", repo_analysis.run)
    graph.add_node("planner", planner.run)
    graph.add_node("executor", executor.run)
    graph.add_node("reviewer", reviewer.run)
    graph.add_node("finalizer", finalizer.run)

    graph.set_entry_point("intent_router")

    # intent_router → repo_analysis | intent_router
    graph.add_conditional_edges(
        "intent_router",
        lambda state: ("intent_router" if state.status == AgentStatus.WAITING_FOR_USER else "repo_analysis"),
    )

    graph.add_edge("repo_analysis", "planner")
    graph.add_edge("planner", "executor")
    graph.add_edge("executor", "reviewer")

    # reviewer → finalizer | planner
    graph.add_conditional_edges(
        "reviewer",
        lambda state: ("finalizer" if state.approval is True else "planner"),
    )

    graph.add_edge("finalizer", END)

    return graph.compile()
