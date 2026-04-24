"""Routing after self_eval (section regen vs patch vs writer)."""

from langgraph.types import Send

from osa_tool.operations.docs.readme_generation.pipeline.graph import _route_after_self_eval
from osa_tool.operations.docs.readme_generation.pipeline.models import SectionSpec
from osa_tool.operations.docs.readme_generation.pipeline.state import ReadmeState


def _minimal_state(**kwargs: object) -> ReadmeState:
    base = {
        "repo_url": "https://example.com/repo",
        "refinement_cycles": 1,
        "max_refinement_cycles": 3,
        "refinement_effective_finish": False,
        "refinement_issues": [],
        "sections_to_rerun": [],
        "section_plan": [],
    }
    base.update(kwargs)
    return ReadmeState.model_validate(base)


def test_route_max_cycles_sends_writer_even_with_pending_rerun() -> None:
    plan = [SectionSpec(name="overview", title="Overview", strategy="llm")]
    state = _minimal_state(
        refinement_cycles=3,
        max_refinement_cycles=3,
        sections_to_rerun=["overview"],
        section_plan=plan,
        refinement_effective_finish=False,
        refinement_issues=["(major) still broken"],
    )
    assert _route_after_self_eval(state) == "writer"


def test_route_section_regeneration_before_effective_finish() -> None:
    plan = [SectionSpec(name="overview", title="Overview", strategy="llm")]
    state = _minimal_state(
        refinement_cycles=1,
        sections_to_rerun=["overview"],
        section_plan=plan,
        refinement_effective_finish=True,
        refinement_issues=["(major) should not skip regen"],
    )
    out = _route_after_self_eval(state)
    assert isinstance(out, list)
    assert len(out) == 1
    assert isinstance(out[0], Send)


def test_route_effective_finish_to_writer() -> None:
    state = _minimal_state(
        refinement_effective_finish=True,
        refinement_issues=[],
        sections_to_rerun=[],
    )
    assert _route_after_self_eval(state) == "writer"


def test_route_issues_to_readme_patch() -> None:
    state = _minimal_state(
        refinement_effective_finish=False,
        refinement_issues=["(major) fix contradiction"],
        sections_to_rerun=[],
    )
    assert _route_after_self_eval(state) == "readme_patch"


def test_route_no_work_to_writer() -> None:
    state = _minimal_state(
        refinement_effective_finish=False,
        refinement_issues=[],
        sections_to_rerun=[],
    )
    assert _route_after_self_eval(state) == "writer"
