from unittest.mock import MagicMock, patch

from osa_tool.operations.docs.readme_generation.agent.models import (
    RepositoryContext,
    SectionResult,
    SectionSpec,
    TaskIntent,
)
from osa_tool.operations.docs.readme_generation.agent.nodes.assembler import assembler_node
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState


def test_assembler_node_calls_merge_llm_for_partial_improve_with_existing_readme() -> None:
    # Arrange
    state = ReadmeState(
        repo_url="https://github.com/o/r",
        intent=TaskIntent(scope="partial", task_type="improve", affected_sections=["usage"]),
        context=RepositoryContext(existing_readme="# X\n"),
        section_plan=[SectionSpec(name="usage", title="Usage", strategy="llm", priority=16)],
        sections={
            "usage": SectionResult(name="usage", title="Usage", content="new", source="llm"),
        },
    )
    context = MagicMock()
    context.prompts.get.return_value = ""
    context.model_handler.send_and_parse.return_value = MagicMock(text="MERGED_IMPROVE")

    # Act
    with patch(
        "osa_tool.operations.docs.readme_generation.agent.nodes.assembler.PromptBuilder.render",
        return_value="prompt",
    ):
        result = assembler_node(state, context)

    # Assert
    assert result["readme_draft"] == "MERGED_IMPROVE"
    context.model_handler.send_and_parse.assert_called_once()


def test_assembler_node_calls_merge_llm_for_partial_update_with_existing_readme() -> None:
    # Arrange
    state = ReadmeState(
        repo_url="https://github.com/o/r",
        intent=TaskIntent(scope="partial", task_type="update", affected_sections=["usage"]),
        context=RepositoryContext(existing_readme="# X\n"),
        section_plan=[SectionSpec(name="usage", title="Usage", strategy="llm", priority=16)],
        sections={
            "usage": SectionResult(name="usage", title="Usage", content="new", source="llm"),
        },
    )
    context = MagicMock()
    context.prompts.get.return_value = ""
    context.model_handler.send_and_parse.return_value = MagicMock(text="MERGED_README")

    # Act
    with patch(
        "osa_tool.operations.docs.readme_generation.agent.nodes.assembler.PromptBuilder.render",
        return_value="prompt",
    ):
        result = assembler_node(state, context)

    # Assert
    assert result["readme_draft"] == "MERGED_README"
    context.model_handler.send_and_parse.assert_called_once()


def test_assembler_node_skips_merge_llm_for_full_compose_mode() -> None:
    # Arrange
    state = ReadmeState(
        repo_url="https://github.com/o/r",
        intent=TaskIntent(scope="full"),
        context=RepositoryContext(existing_readme="# X\n"),
        section_plan=[SectionSpec(name="header", title="Header", strategy="deterministic", priority=0)],
        sections={
            "header": SectionResult(name="header", title="Header", content="# Project", source="deterministic"),
        },
    )
    context = MagicMock()

    # Act
    result = assembler_node(state, context)

    # Assert
    context.model_handler.send_and_parse.assert_not_called()
    assert "# Project" in result["readme_draft"]
