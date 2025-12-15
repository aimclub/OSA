from langgraph.graph import StateGraph

from osa_tool.osa_agent.config import OSAAgentConfig
from osa_tool.osa_agent.nodes.planner_node import OSAPlannerNode
from osa_tool.osa_agent.state import OSAAgentState


def create_agent_graph(agent_config: OSAAgentConfig):
    """
    Create a LangGraph workflow with planner node.
    """
    # Create the graph
    workflow = StateGraph(OSAAgentState)

    # Create planner node
    planner_node = OSAPlannerNode(agent_config)

    # Add nodes to the graph
    workflow.add_node("planner", planner_node)

    # Define the flow (only planner for now)
    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "__end__")

    # Compile the graph
    graph = workflow.compile()

    return graph
