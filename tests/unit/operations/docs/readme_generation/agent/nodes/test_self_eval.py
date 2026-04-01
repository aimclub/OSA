from osa_tool.operations.docs.readme_generation.agent.models import SectionSpec
from osa_tool.operations.docs.readme_generation.agent.nodes.self_eval import _filter_sections_to_rerun


def test_filter_sections_to_rerun_keeps_only_planned_llm_sections() -> None:
    # Arrange
    plan = [
        SectionSpec(name="overview", title="Overview", strategy="llm"),
        SectionSpec(name="header", title="Header", strategy="deterministic"),
    ]
    candidates = ["overview", "header", "bogus"]

    # Act
    filtered = _filter_sections_to_rerun(candidates, plan)

    # Assert
    assert filtered == ["overview"]
