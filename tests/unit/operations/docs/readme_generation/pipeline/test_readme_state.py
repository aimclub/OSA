from osa_tool.operations.docs.readme_generation.pipeline.models import RepositoryContext, TaskIntent
from osa_tool.operations.docs.readme_generation.pipeline.state import ReadmeState


def _state(**kwargs) -> ReadmeState:
    return ReadmeState(repo_url="https://example.com/o/r", **kwargs)


def test_readme_assembly_mode_merge_existing_when_partial_and_real_readme() -> None:
    # Arrange
    state = _state(
        intent=TaskIntent(scope="partial", task_type="improve", affected_sections=["usage"]),
        context=RepositoryContext(existing_readme="# Title\n\nHello"),
    )

    # Act
    assembly_mode = state.readme_assembly_mode()

    # Assert
    assert assembly_mode == "merge_existing"


def test_readme_assembly_mode_full_compose_when_partial_but_empty_readme() -> None:
    # Arrange
    state = _state(
        intent=TaskIntent(scope="partial"),
        context=RepositoryContext(existing_readme=""),
    )

    # Act
    assembly_mode = state.readme_assembly_mode()

    # Assert
    assert assembly_mode == "full_compose"


def test_readme_assembly_mode_full_compose_when_scope_is_full() -> None:
    # Arrange
    state = _state(
        intent=TaskIntent(scope="full"),
        context=RepositoryContext(existing_readme="# Hi"),
    )

    # Act
    assembly_mode = state.readme_assembly_mode()

    # Assert
    assert assembly_mode == "full_compose"
