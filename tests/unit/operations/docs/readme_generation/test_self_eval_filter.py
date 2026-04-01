"""Tests for self-eval sections_to_rerun filtering."""

from osa_tool.operations.docs.readme_generation.agent.models import SectionSpec
from osa_tool.operations.docs.readme_generation.agent.nodes.self_eval import _filter_sections_to_rerun


def test_filter_keeps_planned_llm_sections_only() -> None:
    plan = [
        SectionSpec(name="overview", title="Overview", strategy="llm"),
        SectionSpec(name="header", title="Header", strategy="deterministic"),
    ]
    assert _filter_sections_to_rerun(["overview", "header", "bogus"], plan) == ["overview"]
