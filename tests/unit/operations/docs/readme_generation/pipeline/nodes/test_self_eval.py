from osa_tool.operations.docs.readme_generation.pipeline.llm_schemas import ReadmeSelfEvalLLMOutput, SelfEvalIssue
from osa_tool.operations.docs.readme_generation.pipeline.models import SectionSpec
from osa_tool.operations.docs.readme_generation.pipeline.nodes.self_eval import (
    _compute_effective_finish,
    _derived_refinement_score,
    _filter_sections_to_rerun,
    _structured_issues_to_strings,
)


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


def test_structured_issues_to_strings_formats_and_skips_empty() -> None:
    issues = [
        SelfEvalIssue(severity="blocker", description="wrong repo name"),
        SelfEvalIssue(severity="minor", description=""),
    ]
    assert _structured_issues_to_strings(issues) == ["(blocker) wrong repo name"]


def test_structured_issues_to_strings_placeholder_for_empty_blocker_or_major() -> None:
    issues = [
        SelfEvalIssue(severity="major", description=""),
        SelfEvalIssue(severity="blocker", description="   "),
    ]
    out = _structured_issues_to_strings(issues)
    assert out == [
        "(major) (no description provided)",
        "(blocker) (no description provided)",
    ]


def test_derived_refinement_score_reflects_severities() -> None:
    empty: list[SelfEvalIssue] = []
    assert _derived_refinement_score(empty) == 10.0
    one_major = [SelfEvalIssue(severity="major", description="x")]
    assert _derived_refinement_score(one_major) == 8.0
    one_blocker = [SelfEvalIssue(severity="blocker", description="x")]
    assert _derived_refinement_score(one_blocker) == 7.0


def test_effective_finish_requires_stop_without_blocker_major_or_rerun() -> None:
    assert _compute_effective_finish(
        True,
        [SelfEvalIssue(severity="minor", description="typo")],
        [],
    )
    assert not _compute_effective_finish(
        True,
        [SelfEvalIssue(severity="major", description="gap")],
        [],
    )
    assert not _compute_effective_finish(True, [], ["overview"])
    assert not _compute_effective_finish(False, [], [])


def test_readme_self_eval_coerces_legacy_string_issues() -> None:
    parsed = ReadmeSelfEvalLLMOutput.model_validate(
        {
            "issues": ["legacy issue one", "  ", "legacy two"],
            "should_stop": False,
            "score": 7,
        }
    )
    assert len(parsed.issues) == 2
    assert parsed.issues[0].severity == "major"
    assert parsed.issues[0].description == "legacy issue one"
    assert parsed.issues[1].description == "legacy two"
