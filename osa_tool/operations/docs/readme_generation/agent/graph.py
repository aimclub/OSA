from typing import Any, Union

from langgraph.constants import END
from langgraph.types import Send
from langgraph.graph import StateGraph

from osa_tool.operations.docs.readme_generation.agent.context import ReadmeContext
from osa_tool.operations.docs.readme_generation.agent.nodes import (
    algorithms_node,
    content_node,
    context_collector_node,
    core_features_node,
    diagnosis_node,
    file_summary_node,
    getting_started_node,
    overview_node,
    pdf_summary_node,
    refiner_node,
    section_assembler_node,
    writer_node,
)
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState


def _route_after_diagnosis(state: ReadmeState) -> Union[str, list[Send]]:
    """Route based on generation_mode and readme_mode after diagnosis.

    - targeted  → section_assembler directly (no content generation)
    - article   → file_summary ∥ pdf_summary  (parallel via Send)
    - standard  → core_features (sequential; fan-out happens after core_features)
    """
    if state.generation_mode == "targeted":
        return "section_assembler"

    if state.readme_mode == "article":
        return [
            Send("file_summary", state),
            Send("pdf_summary", state),
        ]

    # Standard: core_features runs first so overview can use its output.
    # Fan-out to overview ∥ getting_started happens via _route_after_core_features.
    return "core_features"


def _route_after_core_features(state: ReadmeState) -> list[Send]:
    """Fan-out from core_features to overview ∥ getting_started in the same superstep.

    Both nodes complete together, so section_assembler is triggered once (deduplicated).
    """
    return [
        Send("overview", state),
        Send("getting_started", state),
    ]


def _route_after_summaries(state: ReadmeState) -> list[Send]:
    """After file_summary + pdf_summary fan-in, fan-out to article content nodes.

    All four complete in the same superstep so section_assembler is triggered once.
    """
    return [
        Send("overview", state),
        Send("content", state),
        Send("algorithms", state),
        Send("getting_started", state),
    ]


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

    # ── Nodes ──
    graph.add_node("context_collector", lambda state: context_collector_node(state, context))
    graph.add_node("diagnosis", lambda state: diagnosis_node(state, context))

    # Standard mode
    graph.add_node("core_features", lambda state: core_features_node(state, context))
    graph.add_node("getting_started", lambda state: getting_started_node(state, context))
    graph.add_node("overview", lambda state: overview_node(state, context))

    # Article mode
    graph.add_node("file_summary", lambda state: file_summary_node(state, context))
    graph.add_node("pdf_summary", lambda state: pdf_summary_node(state, context))
    graph.add_node("content", lambda state: content_node(state, context))
    graph.add_node("algorithms", lambda state: algorithms_node(state, context))

    # Fan-in node: waits for file_summary + pdf_summary before article fan-out
    graph.add_node("summary_fan_in", lambda state: {})

    # Assembly, refinement, output
    graph.add_node("section_assembler", lambda state: section_assembler_node(state, context))
    graph.add_node("refiner", lambda state: refiner_node(state, context))
    graph.add_node("writer", lambda state: writer_node(state, context))

    # ── Entry ──
    graph.set_entry_point("context_collector")
    graph.add_edge("context_collector", "diagnosis")

    # ── After diagnosis: route to targeted / article / standard ──
    graph.add_conditional_edges("diagnosis", _route_after_diagnosis)

    # ── Standard mode ──
    # core_features → fan-out → overview ∥ getting_started (same superstep)
    # Both trigger section_assembler in the same superstep → deduplicated → runs once.
    graph.add_conditional_edges("core_features", _route_after_core_features)
    graph.add_edge("overview", "section_assembler")
    graph.add_edge("getting_started", "section_assembler")

    # ── Article mode ──
    # file_summary ∥ pdf_summary → summary_fan_in → fan-out to 4 nodes (same superstep)
    # All four trigger section_assembler in same superstep → deduplicated → runs once.
    graph.add_edge("file_summary", "summary_fan_in")
    graph.add_edge("pdf_summary", "summary_fan_in")
    graph.add_conditional_edges("summary_fan_in", _route_after_summaries)
    graph.add_edge("content", "section_assembler")
    graph.add_edge("algorithms", "section_assembler")
    # overview → section_assembler and getting_started → section_assembler defined above

    # ── Refinement loop ──
    graph.add_edge("section_assembler", "refiner")
    graph.add_conditional_edges(
        "refiner",
        _route_after_refiner,
        {
            "refiner": "refiner",
            "writer": "writer",
        },
    )
    graph.add_edge("writer", END)

    return graph.compile()
