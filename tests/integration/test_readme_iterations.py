"""Integration tests for the README generation pipeline's iterative self-correction loop."""

import pytest
from unittest.mock import MagicMock, patch

from osa_tool.operations.docs.readme_generation.pipeline.state import ReadmeState
from osa_tool.operations.docs.readme_generation.pipeline.graph import build_readme_graph
from osa_tool.operations.docs.readme_generation.pipeline.llm_schemas import ReadmeSelfEvalLLMOutput, SelfEvalIssue
from osa_tool.operations.docs.readme_generation.pipeline.models import SectionSpec


@pytest.mark.asyncio
@patch("osa_tool.operations.docs.readme_generation.pipeline.graph.writer_node", return_value={})
@patch("osa_tool.operations.docs.readme_generation.pipeline.graph.readme_patch_node", return_value={})
@patch("osa_tool.operations.docs.readme_generation.pipeline.graph.assembler_node", return_value={})
@patch("osa_tool.operations.docs.readme_generation.pipeline.graph.section_generator_node", return_value={})
@patch("osa_tool.operations.docs.readme_generation.pipeline.graph.section_planner_node", return_value={})
@patch("osa_tool.operations.docs.readme_generation.pipeline.graph.intent_analyzer_node", return_value={})
@patch("osa_tool.operations.docs.readme_generation.pipeline.graph.context_collector_node", return_value={})
async def test_readme_self_correction_loop(
    mock_context, mock_intent, mock_planner, mock_generator, mock_assembler, mock_patch, mock_writer
):
    """
    Tests the self-evaluation and refinement cycle of the README generation graph.
    All nodes except `self_eval_node` are mocked to isolate the routing logic.
    """
    state = ReadmeState(
        repo_url="https://github.com/fake/repo",
        user_request="Make a good readme",
        max_refinement_cycles=3,
        section_plan=[SectionSpec(name="Overview", title="Overview", strategy="llm", tools=[])],
    )

    ctx = MagicMock()
    ctx.model_handler = MagicMock()
    ctx.prompts = MagicMock()
    ctx.prompts.get.return_value = "fake_prompt"

    def mock_send_and_parse(*args, **kwargs):
        parser = kwargs.get("parser")

        if parser == ReadmeSelfEvalLLMOutput:
            mock_send_and_parse.eval_call_count = getattr(mock_send_and_parse, "eval_call_count", 0) + 1

            if mock_send_and_parse.eval_call_count == 1:
                # ИТЕРАЦИЯ 1: Комплексный провал по нескольким параметрам
                return ReadmeSelfEvalLLMOutput(
                    should_stop=False,
                    issues=[
                        SelfEvalIssue(
                            severity="blocker", description="CRITICAL: Missing installation and setup instructions."
                        ),
                        SelfEvalIssue(
                            severity="warning",
                            description="FORMATTING: Inconsistent Markdown headers and missing code blocks.",
                        ),
                    ],
                    sections_to_rerun=["Overview"],
                    section_feedback={
                        "Overview": "Rewrite to include setup steps, fix Markdown formatting, and enforce strictly English."
                    },
                    quality_notes="Failed multiple quality checks: missing dependencies info, bad formatting, wrong language.",
                )
            else:

                return ReadmeSelfEvalLLMOutput(
                    should_stop=True,
                    issues=[],
                    sections_to_rerun=[],
                    section_feedback={},
                    quality_notes="Passed all quality metrics: structure, formatting, and language are perfect.",
                )
        return MagicMock()

    ctx.model_handler.send_and_parse.side_effect = mock_send_and_parse

    graph = build_readme_graph(ctx)
    final_state_raw = await graph.ainvoke(state.model_dump())
    final_state = ReadmeState.model_validate(final_state_raw)

    assert final_state.refinement_cycles == 2, f"Expected 2 cycles, got {final_state.refinement_cycles}"
    assert final_state.refinement_effective_finish is True, "Graph finished with unresolved errors"
    assert (
        len(final_state.refinement_structured_issues) == 0
    ), "Issues list should be empty on final successful iteration"
