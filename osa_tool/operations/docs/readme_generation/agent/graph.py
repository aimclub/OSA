"""LangGraph definition for the README generation pipeline.

Topology:
    context_collector -> intent_analyzer -> section_planner
        -> fan-out section_generator x N (LLM + deterministic per SectionSpec)
        -> assembler -> self_eval -> (section_generator regen fan-out | readme_patch | writer)
        -> writer -> END
"""

from collections.abc import Mapping
from typing import Any

from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.types import Send

from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.nodes.assembler import assembler_node
from osa_tool.operations.docs.readme_generation.agent.nodes.context_collector import context_collector_node
from osa_tool.operations.docs.readme_generation.agent.nodes.intent_analyzer import intent_analyzer_node
from osa_tool.operations.docs.readme_generation.agent.nodes.readme_patch import readme_patch_node
from osa_tool.operations.docs.readme_generation.agent.nodes.section_generator import section_generator_node
from osa_tool.operations.docs.readme_generation.agent.nodes.section_planner import section_planner_node
from osa_tool.operations.docs.readme_generation.agent.nodes.self_eval import self_eval_node
from osa_tool.operations.docs.readme_generation.agent.nodes.writer import writer_node
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState


def _ensure_state(state: ReadmeState | Mapping[str, Any]) -> ReadmeState:
    """LangGraph Send delivers a raw dict — rehydrate into ReadmeState."""
    if isinstance(state, ReadmeState):
        return state
    return ReadmeState.model_validate(state)


def _fan_out_to_generators(state: ReadmeState) -> list[Send]:
    """Fan-out from section_planner: one section_generator Send per planned LLM/deterministic section."""
    sends: list[Send] = []
    for spec in state.section_plan:
        if spec.strategy in ("llm", "deterministic"):
            sends.append(Send("section_generator", state.model_copy(update={"current_section": spec}).model_dump()))
    return sends


def _build_section_regeneration_sends(state: ReadmeState) -> list[Send]:
    """Rebuild LLM sections requested by self-eval (catalog names only)."""
    plan_by_name = {s.name: s for s in state.section_plan}
    seen: set[str] = set()
    sends: list[Send] = []
    for name in state.sections_to_rerun:
        n = (name or "").strip()
        if not n or n in seen:
            continue
        seen.add(n)
        spec = plan_by_name.get(n)
        if spec is not None and spec.strategy == "llm":
            sends.append(Send("section_generator", state.model_copy(update={"current_section": spec}).model_dump()))
    return sends


def _route_after_self_eval(state: ReadmeState) -> str | list[Send]:
    if state.refinement_score is not None and state.refinement_score >= 8.0:
        return "writer"
    if state.refinement_cycles >= state.max_refinement_cycles:
        return "writer"
    sends = _build_section_regeneration_sends(state)
    if sends:
        return sends
    if state.refinement_issues:
        return "readme_patch"
    return "writer"


def build_readme_graph(context: ReadmeContext) -> Any:
    """Build and compile the README generation LangGraph."""
    graph = StateGraph(ReadmeState)

    graph.add_node("context_collector", lambda s: context_collector_node(s, context))
    graph.add_node("intent_analyzer", lambda s: intent_analyzer_node(s, context))
    graph.add_node("section_planner", lambda s: section_planner_node(s, context))
    graph.add_node("section_generator", lambda s: section_generator_node(_ensure_state(s), context))
    graph.add_node("assembler", lambda s: assembler_node(s, context))
    graph.add_node("self_eval", lambda s: self_eval_node(s, context))
    graph.add_node("readme_patch", lambda s: readme_patch_node(s, context))
    graph.add_node("writer", lambda s: writer_node(s))

    graph.set_entry_point("context_collector")
    graph.add_edge("context_collector", "intent_analyzer")
    graph.add_edge("intent_analyzer", "section_planner")
    graph.add_conditional_edges("section_planner", _fan_out_to_generators)
    graph.add_edge("section_generator", "assembler")
    graph.add_edge("assembler", "self_eval")
    graph.add_conditional_edges("self_eval", _route_after_self_eval)
    graph.add_edge("readme_patch", "self_eval")
    graph.add_edge("writer", END)

    return graph.compile()
