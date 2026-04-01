"""Tests for assembler merge vs full-compose routing."""

from unittest.mock import MagicMock, patch

from osa_tool.operations.docs.readme_generation.agent.models import (
    RepositoryContext,
    SectionResult,
    SectionSpec,
    TaskIntent,
)
from osa_tool.operations.docs.readme_generation.agent.nodes.assembler import assembler_node
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState


def test_merge_path_calls_llm_when_partial_improve_and_real_readme() -> None:
    """Partial scope uses merge path even when task_type is improve (not only update)."""
    state = ReadmeState(
        repo_url="https://github.com/o/r",
        intent=TaskIntent(scope="partial", task_type="improve", affected_sections=["usage"]),
        context=RepositoryContext(existing_readme="# X\n"),
        section_plan=[SectionSpec(name="usage", title="Usage", strategy="llm", priority=16)],
        sections={
            "usage": SectionResult(name="usage", title="Usage", content="new", source="llm"),
        },
    )
    ctx = MagicMock()
    ctx.prompts.get.return_value = ""
    ctx.model_handler.send_and_parse.return_value = MagicMock(text="MERGED_IMPROVE")
    with patch(
        "osa_tool.operations.docs.readme_generation.agent.nodes.assembler.PromptBuilder.render",
        return_value="prompt",
    ):
        out = assembler_node(state, ctx)
    assert out["readme_draft"] == "MERGED_IMPROVE"
    ctx.model_handler.send_and_parse.assert_called_once()


def test_merge_path_calls_llm_when_partial_update_and_real_readme() -> None:
    state = ReadmeState(
        repo_url="https://github.com/o/r",
        intent=TaskIntent(scope="partial", task_type="update", affected_sections=["usage"]),
        context=RepositoryContext(existing_readme="# X\n"),
        section_plan=[SectionSpec(name="usage", title="Usage", strategy="llm", priority=16)],
        sections={
            "usage": SectionResult(name="usage", title="Usage", content="new", source="llm"),
        },
    )
    ctx = MagicMock()
    ctx.prompts.get.return_value = ""
    ctx.model_handler.send_and_parse.return_value = MagicMock(text="MERGED_README")
    with patch(
        "osa_tool.operations.docs.readme_generation.agent.nodes.assembler.PromptBuilder.render",
        return_value="prompt",
    ):
        out = assembler_node(state, ctx)
    assert out["readme_draft"] == "MERGED_README"
    ctx.model_handler.send_and_parse.assert_called_once()


def test_full_compose_does_not_call_merge_llm() -> None:
    state = ReadmeState(
        repo_url="https://github.com/o/r",
        intent=TaskIntent(scope="full"),
        context=RepositoryContext(existing_readme="# X\n"),
        section_plan=[
            SectionSpec(name="header", title="Header", strategy="deterministic", priority=0),
        ],
        sections={
            "header": SectionResult(name="header", title="Header", content="# Project", source="deterministic"),
        },
    )
    ctx = MagicMock()
    out = assembler_node(state, ctx)
    ctx.model_handler.send_and_parse.assert_not_called()
    assert "# Project" in out["readme_draft"]
