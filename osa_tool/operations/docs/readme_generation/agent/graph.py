"""LangGraph definition for the README generation pipeline.

Topology:
    context_collector -> intent_analyzer -> section_planner
        -> fan-out (section_generator x N || deterministic_builder)
        -> assembler -> refiner (loop) -> writer -> END
"""

from __future__ import annotations

from typing import Any

from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.types import Send

from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.nodes.assembler import assembler_node
from osa_tool.operations.docs.readme_generation.agent.nodes.context_collector import context_collector_node
from osa_tool.operations.docs.readme_generation.agent.nodes.deterministic_builder import deterministic_builder_node
from osa_tool.operations.docs.readme_generation.agent.nodes.intent_analyzer import intent_analyzer_node
from osa_tool.operations.docs.readme_generation.agent.nodes.refiner import refiner_node
from osa_tool.operations.docs.readme_generation.agent.nodes.section_generator import section_generator_node
from osa_tool.operations.docs.readme_generation.agent.nodes.section_planner import section_planner_node
from osa_tool.operations.docs.readme_generation.agent.nodes.writer import writer_node
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState


def _ensure_state(s: Any) -> ReadmeState:
    """LangGraph Send delivers a raw dict — rehydrate into ReadmeState."""
    if isinstance(s, ReadmeState):
        return s
    return ReadmeState.model_validate(s)


def _fan_out_to_generators(state: ReadmeState) -> list[Send]:
    """Fan-out from section_planner to parallel section generators.

    Each LLM section gets its own ``section_generator`` invocation via Send.
    All deterministic sections are handled by a single ``deterministic_builder`` call.
    """
    sends: list[Send] = []
    has_deterministic = False

    for spec in state.section_plan:
        if spec.strategy == "llm":
            sends.append(Send("section_generator", state.model_copy(update={"current_section": spec}).model_dump()))
        elif spec.strategy == "deterministic":
            has_deterministic = True

    if has_deterministic:
        sends.append(Send("deterministic_builder", state.model_dump()))

    return sends


def _route_after_refiner(state: ReadmeState) -> str:
    """Continue refining or proceed to writer."""
    if state.refinement_score is not None and state.refinement_score >= 8.0:
        return "writer"
    if state.refinement_cycles >= state.max_refinement_cycles:
        return "writer"
    return "refiner"


def build_readme_graph(context: ReadmeContext) -> Any:
    """Build and compile the README generation LangGraph."""
    graph = StateGraph(ReadmeState)

    # ── Register nodes ──
    graph.add_node("context_collector", lambda s: context_collector_node(s, context))
    graph.add_node("intent_analyzer", lambda s: intent_analyzer_node(s, context))
    graph.add_node("section_planner", lambda s: section_planner_node(s, context))
    graph.add_node("section_generator", lambda s: section_generator_node(_ensure_state(s), context))
    graph.add_node("deterministic_builder", lambda s: deterministic_builder_node(_ensure_state(s), context))
    graph.add_node("assembler", lambda s: assembler_node(s, context))
    graph.add_node("refiner", lambda s: refiner_node(s, context))
    graph.add_node("writer", lambda s: writer_node(s, context))

    # ── Sequential edges ──
    graph.set_entry_point("context_collector")
    graph.add_edge("context_collector", "intent_analyzer")
    graph.add_edge("intent_analyzer", "section_planner")

    # ── Parallel fan-out: section_planner -> N generators + deterministic_builder ──
    graph.add_conditional_edges("section_planner", _fan_out_to_generators)

    # ── Fan-in: all generators / deterministic_builder -> assembler ──
    graph.add_edge("section_generator", "assembler")
    graph.add_edge("deterministic_builder", "assembler")

    # ── Refinement loop ──
    graph.add_edge("assembler", "refiner")
    graph.add_conditional_edges(
        "refiner",
        _route_after_refiner,
        {"refiner": "refiner", "writer": "writer"},
    )

    graph.add_edge("writer", END)

    return graph.compile()
