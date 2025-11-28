from typing import Dict, Any, List, Optional

from pydantic import BaseModel

from osa_tool.ui.input_for_chat import InitialChatInput


class AgentState(BaseModel):
    """
    Global agent state passed between LangGraph nodes.
    This object accumulates all information needed for reasoning and actions.
    """

    user_input: InitialChatInput
    """User-provided initial request, including repo_url and high-level goal."""

    parameters: Dict[str, Any] = {}
    """Parameters extracted or inferred by the planner or sub-agents."""

    context: Dict[str, Any] = {}
    """Arbitrary context: repository metadata, analysis results, etc."""

    messages: List[Dict[str, Any]] = []
    """LLM message history for multi-step reasoning."""

    last_planner_output: Optional[Any] = None
    """Raw last output from PlannerNode."""
