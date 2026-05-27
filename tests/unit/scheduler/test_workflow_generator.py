import pytest
import yaml

from osa_tool.config.settings import WorkflowSettings
from osa_tool.core.models.task import TaskStatus
from osa_tool.operations.codebase.workflow_generation.workflow_generator import SourceCraftWorkflowGenerator
from osa_tool.scheduler.plan import Plan


def _settings(**kwargs) -> WorkflowSettings:
    defaults = dict(
        include_black=False,
        include_tests=False,
        include_pep8=False,
        include_autopep8=False,
        include_fix_pep8=False,
        include_pypi=False,
        python_versions=["3.11"],
        pep8_tool="flake8",
        use_poetry=False,
        branches=[],
        codecov_token=False,
        include_codecov=False,
    )
    defaults.update(kwargs)
    return WorkflowSettings(**defaults)


def _load_ci(tmp_path) -> dict:
    with open(tmp_path / "ci.yaml") as f:
        return yaml.safe_load(f)


def test_no_flags_returns_empty(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    result = gen.generate_selected_jobs(_settings(), plan=None)
    assert result == []
    assert not (tmp_path / "ci.yaml").exists()


def test_any_flag_creates_ci_yaml(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    result = gen.generate_selected_jobs(_settings(include_black=True), plan=None)
    assert len(result) == 1
    assert (tmp_path / "ci.yaml").exists()


def test_black_cube_in_lint_workflow(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_black=True), plan=None)
    config = _load_ci(tmp_path)
    cubes = config["workflows"]["lint"]["tasks"][0]["cubes"]
    assert any(c["name"] == "black" for c in cubes)


def test_pep8_flake8_cube_in_lint_workflow(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_pep8=True, pep8_tool="flake8"), plan=None)
    config = _load_ci(tmp_path)
    cubes = config["workflows"]["lint"]["tasks"][0]["cubes"]
    assert any(c["name"] == "flake8" for c in cubes)


def test_pep8_pylint_cube_in_lint_workflow(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_pep8=True, pep8_tool="pylint"), plan=None)
    config = _load_ci(tmp_path)
    cubes = config["workflows"]["lint"]["tasks"][0]["cubes"]
    assert any(c["name"] == "pylint" for c in cubes)


def test_autopep8_cube_in_lint_workflow(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_autopep8=True), plan=None)
    config = _load_ci(tmp_path)
    cubes = config["workflows"]["lint"]["tasks"][0]["cubes"]
    assert any(c["name"] == "autopep8" for c in cubes)


def test_fix_pep8_cube_in_lint_workflow(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_fix_pep8=True), plan=None)
    config = _load_ci(tmp_path)
    cubes = config["workflows"]["lint"]["tasks"][0]["cubes"]
    assert any(c["name"] == "fix-pep8" for c in cubes)


def test_combined_lint_cubes(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_black=True, include_pep8=True), plan=None)
    config = _load_ci(tmp_path)
    cubes = config["workflows"]["lint"]["tasks"][0]["cubes"]
    cube_names = {c["name"] for c in cubes}
    assert "black" in cube_names
    assert "flake8" in cube_names


def test_tests_workflow_one_cube_per_version(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_tests=True, python_versions=["3.9", "3.10", "3.11"]), plan=None)
    config = _load_ci(tmp_path)
    cubes = config["workflows"]["tests"]["tasks"][0]["cubes"]
    assert len(cubes) == 3
    cube_names = {c["name"] for c in cubes}
    assert "pytest-3.9" in cube_names
    assert "pytest-3.10" in cube_names
    assert "pytest-3.11" in cube_names


def test_tests_cube_uses_correct_docker_image(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_tests=True, python_versions=["3.10"]), plan=None)
    config = _load_ci(tmp_path)
    cube = config["workflows"]["tests"]["tasks"][0]["cubes"][0]
    assert "python:3.10" in cube["image"]


def test_publish_workflow_created(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_pypi=True), plan=None)
    config = _load_ci(tmp_path)
    assert "publish" in config["workflows"]


def test_publish_triggered_on_version_tags(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_pypi=True), plan=None)
    config = _load_ci(tmp_path)
    push_entries = config["on"]["push"]
    tag_entry = next((e for e in push_entries if e.get("filter", {}).get("tags")), None)
    assert tag_entry is not None
    assert "*.*.*" in tag_entry["filter"]["tags"]


def test_publish_with_poetry(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_pypi=True, use_poetry=True), plan=None)
    config = _load_ci(tmp_path)
    cube = config["workflows"]["publish"]["tasks"][0]["cubes"][0]
    assert any("poetry" in step for step in cube["script"])


def test_publish_with_twine(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_pypi=True, use_poetry=False), plan=None)
    config = _load_ci(tmp_path)
    cube = config["workflows"]["publish"]["tasks"][0]["cubes"][0]
    assert any("twine" in step for step in cube["script"])


def test_generate_selected_jobs_preserves_existing_workflows(tmp_path):
    """Existing docs workflows (build_docs, deploy_docs) must survive a second generate call."""
    # Arrange: ci.yaml already has lint/tests + docs workflows from create_mkdocs_git_workflow
    existing = {
        "on": {
            "push": [
                {"workflows": ["lint", "tests"]},
                {"workflows": ["deploy_docs"], "filter": {"branches": ["main"]}},
            ],
            "pull_request": [{"workflows": ["lint", "tests", "build_docs"]}],
        },
        "workflows": {
            "lint": {"tasks": []},
            "tests": {"tasks": []},
            "build_docs": {"tasks": [{"name": "build_docs", "cubes": []}]},
            "deploy_docs": {"tasks": [{"name": "deploy_docs", "cubes": []}]},
        },
    }
    ci_path = tmp_path / "ci.yaml"
    with open(ci_path, "w") as f:
        yaml.dump(existing, f)

    # Act: workflow_manager regenerates lint/tests (simulates normal OSA run)
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_black=True, include_tests=True), plan=None)

    # Assert: docs workflows must still be present
    config = _load_ci(tmp_path)
    assert "build_docs" in config["workflows"], "build_docs was lost after second generate"
    assert "deploy_docs" in config["workflows"], "deploy_docs was lost after second generate"
    pr_wfs = config["on"]["pull_request"][0]["workflows"]
    assert "build_docs" in pr_wfs, "build_docs disappeared from pull_request trigger"
    push_entries = config["on"]["push"]
    assert any(
        "deploy_docs" in e.get("workflows", []) for e in push_entries
    ), "deploy_docs disappeared from push trigger"


def test_push_and_pull_request_triggers_for_lint(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_black=True), plan=None)
    config = _load_ci(tmp_path)
    assert "push" in config["on"]
    assert "pull_request" in config["on"]


def test_branch_filter_applied_when_branches_set(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_black=True, branches=["main", "dev"]), plan=None)
    config = _load_ci(tmp_path)
    push_entry = config["on"]["push"][0]
    assert "filter" in push_entry
    assert "main" in push_entry["filter"]["branches"]


def test_no_branch_filter_when_branches_empty(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_black=True, branches=[]), plan=None)
    config = _load_ci(tmp_path)
    push_entry = config["on"]["push"][0]
    assert "filter" not in push_entry


def test_no_yaml_anchors_in_output(tmp_path):
    # PyYAML must not produce &id001/*id001 anchors (was a bug with shared list references)
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_black=True, include_tests=True), plan=None)
    content = (tmp_path / "ci.yaml").read_text()
    assert "&id" not in content
    assert "*id" not in content


def test_plan_tasks_marked_done(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    plan = Plan({"include_black": True, "include_pep8": True, "include_tests": True})
    gen.generate_selected_jobs(
        _settings(include_black=True, include_pep8=True, include_tests=True),
        plan=plan,
    )
    assert plan.tasks["include_black"] == TaskStatus.COMPLETED
    assert plan.tasks["include_pep8"] == TaskStatus.COMPLETED
    assert plan.tasks["include_tests"] == TaskStatus.COMPLETED


def test_plan_none_does_not_raise(tmp_path):
    gen = SourceCraftWorkflowGenerator(str(tmp_path))
    gen.generate_selected_jobs(_settings(include_black=True), plan=None)
    assert (tmp_path / "ci.yaml").exists()
