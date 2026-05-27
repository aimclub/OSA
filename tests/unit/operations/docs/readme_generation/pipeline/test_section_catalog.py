from osa_tool.operations.docs.readme_generation.pipeline.models import RepositoryContext, TaskIntent
from osa_tool.operations.docs.readme_generation.pipeline.section_catalog import deterministic_specs_for_intent


def test_deterministic_specs_for_full_intent_includes_default_sections() -> None:
    # Arrange
    intent = TaskIntent(scope="full")
    context = RepositoryContext()

    # Act
    specs = deterministic_specs_for_intent(intent, context)
    names = {spec.name for spec in specs}

    # Assert
    assert "header" in names
    assert "installation" in names
    assert "table_of_contents" in names


def test_deterministic_specs_for_partial_intent_with_installation_only() -> None:
    # Arrange
    intent = TaskIntent(scope="partial", task_type="update", affected_sections=["installation"])
    context = RepositoryContext()

    # Act
    specs = deterministic_specs_for_intent(intent, context)
    names = {spec.name for spec in specs}

    # Assert
    assert names == {"installation"}


def test_deterministic_specs_for_partial_intent_with_only_llm_section() -> None:
    # Arrange
    intent = TaskIntent(scope="partial", task_type="update", affected_sections=["usage"])
    context = RepositoryContext()

    # Act
    specs = deterministic_specs_for_intent(intent, context)

    # Assert
    assert specs == []


def test_deterministic_specs_for_partial_intent_with_empty_affected_sections() -> None:
    # Arrange
    intent = TaskIntent(scope="partial", task_type="update", affected_sections=[])
    context = RepositoryContext()

    # Act
    specs = deterministic_specs_for_intent(intent, context)
    names = {spec.name for spec in specs}

    # Assert
    assert "header" in names
