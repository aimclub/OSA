from argparse import Namespace
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from osa_tool.core.git.git_agent import GitverseAgent, LocalGitAgent
from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.core.models.task import TaskStatus
from osa_tool.run import initialize_git_platform, main, resolve_publishing_options
from osa_tool.run_chat import main as run_chat_main
from osa_tool.scheduler.plan import Plan
from osa_tool.scheduler.workflow_manager import WorkflowGenerationError


@pytest.fixture
def run_args():
    """Minimal set of arguments needed to walk through `main` without running any task."""
    return Namespace(
        repository="https://github.com/aimclub/OSA",
        no_fork=False,
        no_pull_request=False,
        output=None,
        web_mode=True,
        based_on_date=None,
        ignore_list=None,
        incremental=False,
        target_files=None,
        paper_analysis=False,
    )


@pytest.fixture
def run_plan():
    return Plan({})


@pytest.fixture
def workflow_manager():
    return MagicMock()


@pytest.fixture
def run_environment(run_args, run_plan, workflow_manager, tmp_path):
    """Patch everything `main` talks to and yield the arguments with the fake Git agent."""
    git_agent = MagicMock()
    git_agent.based_on_date = None
    git_agent.clone_dir = str(tmp_path / "OSA")

    parser = MagicMock()
    parser.parse_args.return_value = run_args

    scheduler = MagicMock()
    scheduler.plan = run_plan

    with (
        patch("osa_tool.run.build_parser_from_yaml", return_value=parser),
        patch("osa_tool.run.setup_logging"),
        patch("osa_tool.run.ConfigManager"),
        patch("osa_tool.run.initialize_git_platform", return_value=(git_agent, workflow_manager)),
        patch("osa_tool.run.SourceRank"),
        patch("osa_tool.run.ModeScheduler", return_value=scheduler),
    ):
        yield run_args, git_agent


@pytest.mark.parametrize(
    ("other_events", "status", "code"),
    [
        ([], TaskStatus.FAILED, 1),
        ([OperationEvent(kind=EventKind.WRITTEN, target="success.py")], TaskStatus.PARTIAL, 3),
    ],
)
def test_docstring_failure_sets_cli_exit_code(run_environment, run_plan, other_events, status, code):
    run_plan.generated_plan["docstring"] = True
    analyzed = OperationEvent(kind=EventKind.ANALYZED, target="codebase")
    failed = OperationEvent(kind=EventKind.FAILED, target="example.py", data={"error": "403 Key limit exceeded"})
    with patch("osa_tool.run.DocstringsGenerator") as generator:
        generator.return_value.run.return_value = {"result": None, "events": [analyzed, *other_events, failed]}
        with pytest.raises(SystemExit) as exit_info:
            main()

    assert exit_info.value.code == code
    assert run_plan.tasks["docstring"] == status
    assert run_plan.failure_reasons("docstring") == ["example.py: 403 Key limit exceeded"]


def test_empty_notebook_scan_does_not_make_failed_run_partial(run_environment, run_plan, tmp_path):
    args, _ = run_environment
    args.no_fork = True
    run_plan.generated_plan.update(convert_notebooks=[], docstring=True)
    with (
        patch(
            "osa_tool.operations.codebase.notebook_conversion.notebook_converter.resolve_repo_path",
            return_value=tmp_path,
        ),
        patch("osa_tool.run.DocstringsGenerator", side_effect=RuntimeError("Docstring provider failed")),
    ):
        with pytest.raises(SystemExit) as exit_info:
            main()

    assert exit_info.value.code == 1
    assert run_plan.tasks["convert_notebooks"] == TaskStatus.SKIPPED
    assert run_plan.results["convert_notebooks"]["events"][0].data == {"reason": "no_notebooks_found"}


@pytest.mark.parametrize(
    ("existing_description", "description", "code"),
    [("", "   ", 1), ("Existing description", "", 1), ("", "Useful description", 3)],
)
def test_about_failure_counts_only_new_content(
    run_environment, run_plan, mock_config_manager, existing_description, description, code
):
    args, git_agent = run_environment
    args.no_fork = True
    run_plan.generated_plan["about"] = True
    git_agent.metadata.description = existing_description
    git_agent.metadata.homepage_url = ""
    git_agent.metadata.topics = []
    handler = MagicMock()
    handler.send_request.side_effect = [
        *([] if existing_description else [description]),
        RuntimeError("Topics request failed"),
    ]
    with (
        patch("osa_tool.run.ConfigManager", return_value=mock_config_manager),
        patch(
            "osa_tool.operations.docs.about_generation.about_generator.extract_readme_content", return_value="README"
        ),
        patch(
            "osa_tool.operations.docs.about_generation.about_generator.ModelHandlerFactory.build", return_value=handler
        ),
    ):
        with pytest.raises(SystemExit) as exit_info:
            main()

    assert exit_info.value.code == code
    assert run_plan.failure_reasons("about") == ["about.topics: Topics request failed"]
    outcome = run_plan.results["about"]
    generated = any(event.kind == EventKind.GENERATED for event in outcome["events"])
    assert generated == bool(description.strip())
    if not (existing_description or description.strip()):
        assert outcome["result"] is None


@pytest.mark.parametrize("is_directory", [False, True])
def test_rename_failure_prevents_publication(run_environment, run_plan, mock_config_manager, is_directory):
    _, git_agent = run_environment
    run_plan.generated_plan["translate_dirs"] = True
    repo = Path(git_agent.clone_dir)
    repo.mkdir()
    mock_config_manager.get_git_settings().repository = str(repo)
    if is_directory:
        old_path = repo / "модуль"
        old_path.mkdir()
        (old_path / "__init__.py").write_text("", encoding="utf-8")
    else:
        old_path = repo / "модуль.py"
        old_path.write_text("value = 1\n", encoding="utf-8")
    (repo / "main.py").write_text("import модуль\n", encoding="utf-8")
    handler = MagicMock()
    handler.send_request.return_value = "module"
    with (
        patch("osa_tool.run.ConfigManager", return_value=mock_config_manager),
        patch(
            "osa_tool.operations.codebase.directory_translation.dirs_and_files_translator.ModelHandlerFactory.build",
            return_value=handler,
        ),
        patch("os.rename", side_effect=PermissionError("Rename denied")),
    ):
        with pytest.raises(SystemExit) as exit_info:
            main()

    assert exit_info.value.code == 1
    assert run_plan.tasks["translate_dirs"] == TaskStatus.FAILED
    assert run_plan.tasks["publish"] == TaskStatus.SKIPPED
    assert any("Rename denied" in reason for reason in run_plan.failure_reasons("translate_dirs"))
    assert old_path.exists()
    git_agent.commit_and_push_changes.assert_not_called()
    git_agent.create_pull_request.assert_not_called()


def test_gitverse_about_publication_is_skipped(run_environment, run_plan):
    args, git_agent = run_environment
    args.no_pull_request = True
    run_plan.generated_plan["about"] = True
    gitverse = GitverseAgent.__new__(GitverseAgent)
    gitverse.token = "fixture-token"
    gitverse.repo_url = "https://gitverse.ru/owner/project"
    gitverse.fork_url = "https://gitverse.ru/contributor/project"
    git_agent.update_about_section.side_effect = gitverse.update_about_section

    with patch("osa_tool.run.AboutGenerator") as generator:
        generator.return_value.generate_about_content.return_value = {"result": {"description": "About the project"}}
        with pytest.raises(SystemExit) as exit_info:
            main()

    assert exit_info.value.code == 0
    assert run_plan.tasks["about"] == TaskStatus.COMPLETED
    assert run_plan.tasks["publish_about"] == TaskStatus.SKIPPED


def test_reports_share_a_publication_session(run_environment, run_plan):
    _, git_agent = run_environment
    run_plan.generated_plan["report"] = True
    git_agent.commit_and_push_changes.return_value = False
    git_agent.create_pull_request.return_value = False
    uploaded = []

    @contextmanager
    def publication_session():
        git_agent.upload_report.side_effect = lambda filename, path: uploaded.append(filename)
        yield
        git_agent.upload_report.side_effect = AssertionError("Upload attempted outside its session")

    git_agent.report_upload_session.side_effect = publication_session
    with (
        patch("osa_tool.run.ReportGenerator") as report,
        patch("osa_tool.run.WhatHasBeenDoneReportGenerator") as summary,
    ):
        report.return_value.run.return_value = {"result": {"report": "before.pdf", "path": "/tmp/before.pdf"}}
        summary.return_value.run.return_value = {"result": {"report": "summary.pdf", "path": "/tmp/summary.pdf"}}
        with pytest.raises(SystemExit) as exit_info:
            main()

    assert exit_info.value.code == 0
    assert run_plan.tasks["publish_pr"] == TaskStatus.SKIPPED
    git_agent.report_upload_session.assert_called_once_with()
    assert uploaded == ["before.pdf", "summary.pdf"]


def test_workflow_failure_keeps_clone_and_blocks_publication(
    run_environment, run_plan, workflow_manager, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    _, git_agent = run_environment
    git_agent.clone_repository.side_effect = (tmp_path / "OSA").mkdir
    workflow_manager.update_workflow_config.side_effect = RuntimeError("Invalid workflow settings")
    run_plan.generated_plan.update(report=True, about=True, generate_workflows=True, organize=True, delete_dir=True)
    report = tmp_path / "OSA_report.pdf"
    report.write_bytes(b"%PDF-1.4")
    with (
        patch("osa_tool.run.ReportGenerator") as report_generator,
        patch("osa_tool.run.WhatHasBeenDoneReportGenerator") as summary,
        patch("osa_tool.run.AboutGenerator") as about,
        patch("osa_tool.run.RepoOrganizer") as organizer,
    ):
        report_generator.return_value.run.return_value = {"result": {"report": report.name, "path": str(report)}}
        about.return_value.generate_about_content.return_value = {"result": {"description": "Example"}}
        summary.return_value.run.return_value = {"result": {"report": report.name, "path": str(report)}}
        with pytest.raises(SystemExit) as exit_info:
            main()

    assert exit_info.value.code == 3
    assert run_plan.tasks["generate_workflows"] == TaskStatus.FAILED
    assert run_plan.tasks["publish"] == TaskStatus.SKIPPED
    assert run_plan.tasks["delete_dir"] == TaskStatus.SKIPPED
    assert (tmp_path / "OSA").is_dir()
    organizer.return_value.organize.assert_called_once()
    summary.return_value.run.assert_called_once()
    git_agent.update_about_section.assert_not_called()
    git_agent.commit_and_push_changes.assert_not_called()
    git_agent.create_pull_request.assert_not_called()
    git_agent.upload_report.assert_not_called()


def test_workflow_failure_after_first_file_is_partial(run_environment, run_plan, workflow_manager):
    run_plan.generated_plan["generate_workflows"] = True
    files = [".github/workflows/black.yml"]
    workflow_manager.generate_workflow_files.side_effect = WorkflowGenerationError(OSError("Disk full"), files)

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 3
    assert run_plan.tasks["generate_workflows"] == TaskStatus.PARTIAL
    assert run_plan.results["generate_workflows"]["result"] == {"error": "Disk full", "files": files}


@pytest.mark.parametrize(
    ("method", "task"),
    [("commit_and_push_changes", "publish_push"), ("create_pull_request", "publish_pr")],
)
def test_publication_failure_is_recorded_before_summary(run_environment, run_plan, method, task):
    _, git_agent = run_environment
    getattr(git_agent, method).side_effect = RuntimeError("Remote publication failed")
    run_plan.generated_plan["report"] = True
    with (
        patch("osa_tool.run.ReportGenerator") as report,
        patch("osa_tool.run.WhatHasBeenDoneReportGenerator") as summary,
    ):
        report.return_value.run.return_value = {"result": {"report": "example.pdf"}}

        def build_summary():
            assert run_plan.tasks[task] == TaskStatus.FAILED
            assert run_plan.failure_reasons(task) == ["Remote publication failed"]
            return {}

        summary.return_value.run.side_effect = build_summary
        with pytest.raises(SystemExit) as exit_info:
            main()

    assert exit_info.value.code == 3
    summary.return_value.run.assert_called_once()
    if task == "publish_push":
        git_agent.create_pull_request.assert_not_called()


def test_no_workflows_and_recovered_requirements_are_successful(run_environment, run_plan, workflow_manager):
    workflow_manager.generate_workflow_files.return_value = []
    run_plan.generated_plan.update(generate_workflows=True, requirements=True)
    with patch("osa_tool.run.RequirementsGenerator") as requirements:
        requirements.return_value.generate.return_value = {
            "events": [
                OperationEvent(kind=EventKind.FAILED, target="requirements.txt", data={"recovered": True}),
                OperationEvent(kind=EventKind.GENERATED, target="requirements.txt"),
            ]
        }
        with pytest.raises(SystemExit) as exit_info:
            main()

    assert exit_info.value.code == 0
    assert run_plan.tasks["generate_workflows"] == TaskStatus.SKIPPED
    assert run_plan.tasks["requirements"] == TaskStatus.COMPLETED


def test_summary_alone_does_not_make_a_failed_run_partial(run_environment, run_plan):
    args, _ = run_environment
    args.no_fork = True
    run_plan.generated_plan["report"] = True
    with (
        patch("osa_tool.run.ReportGenerator") as report,
        patch("osa_tool.run.WhatHasBeenDoneReportGenerator") as summary,
    ):
        report.return_value.run.return_value = {"result": {"error": "Report generation failed"}}
        summary.return_value.run.return_value = {"result": {"report": "example_work_summary.pdf"}}
        with pytest.raises(SystemExit) as exit_info:
            main()

    assert exit_info.value.code == 1
    assert run_plan.tasks["report"] == TaskStatus.FAILED
    assert run_plan.tasks["work_summary"] == TaskStatus.COMPLETED


@pytest.mark.parametrize("existed_before", [False, True])
def test_scorecard_summary_precedes_cleanup(run_environment, run_plan, tmp_path, monkeypatch, existed_before):
    monkeypatch.chdir(tmp_path)
    args, git_agent = run_environment
    args.no_fork = True
    clone_dir = tmp_path / "OSA"
    if existed_before:
        clone_dir.mkdir()
    else:
        git_agent.clone_repository.side_effect = clone_dir.mkdir
    run_plan.generated_plan.update(scorecard=True, delete_dir=True)
    with (
        patch("osa_tool.run.ReportGenerator") as report,
        patch("osa_tool.run.WhatHasBeenDoneReportGenerator") as summary,
    ):
        report.return_value.run.return_value = {}

        def build_summary():
            assert clone_dir.is_dir()
            assert run_plan.tasks["report"] == TaskStatus.COMPLETED
            return {}

        summary.return_value.run.side_effect = build_summary
        with pytest.raises(SystemExit) as exit_info:
            main()

    assert exit_info.value.code == 0
    assert clone_dir.exists() == existed_before
    summary.return_value.run.assert_called_once()


def test_main_creates_fork_and_pull_request_by_default(run_environment):
    # Arrange
    _, git_agent = run_environment

    # Act
    with pytest.raises(SystemExit) as exit_info:
        main()

    # Assert
    assert exit_info.value.code == 0
    git_agent.create_fork.assert_called_once()
    git_agent.create_and_checkout_branch.assert_called_once()
    git_agent.create_pull_request.assert_called_once()


def test_main_skips_fork_and_pull_request_for_based_on_date(run_environment):
    # Arrange
    args, git_agent = run_environment
    args.based_on_date = "2021-01-01"
    git_agent.based_on_date = datetime(2021, 1, 1, tzinfo=timezone.utc)

    # Act
    with patch("osa_tool.run.logger") as mock_logger:
        with pytest.raises(SystemExit) as exit_info:
            main()

    # Assert
    assert exit_info.value.code == 0
    git_agent.star_repository.assert_not_called()
    git_agent.create_fork.assert_not_called()
    git_agent.create_and_checkout_branch.assert_not_called()
    git_agent.create_pull_request.assert_not_called()
    git_agent.clone_repository.assert_called_once()

    warnings = [call.args[0] for call in mock_logger.warning.call_args_list]
    assert any("NO FORK" in message and "NO PULL REQUEST" in message for message in warnings)
    assert any("2021-01-01" in message for message in warnings)


def test_initialize_git_platform_passes_based_on_date_from_config(run_args):
    # Arrange
    config_manager = MagicMock()
    config_manager.config.git.based_on_date = datetime(2021, 1, 1, tzinfo=timezone.utc)
    config_manager.config.git.osa_branch_name = "osa_tool"
    run_args.branch = None
    run_args.author = None

    # Act
    with (
        patch("osa_tool.run.GitHubAgent") as mock_github_agent,
        patch("osa_tool.run.GitHubWorkflowManager"),
    ):
        initialize_git_platform(run_args, config_manager)

    # Assert
    assert mock_github_agent.call_args.kwargs["based_on_date"] == datetime(2021, 1, 1, tzinfo=timezone.utc)


def test_resolve_publishing_options_enabled_by_default(run_args):
    # Arrange
    git_agent = MagicMock()
    git_agent.based_on_date = None

    # Act
    create_fork, create_pull_request = resolve_publishing_options(run_args, git_agent)

    # Assert
    assert create_fork is True
    assert create_pull_request is True


def test_resolve_publishing_options_disabled_for_local_agent(run_args):
    # Arrange
    git_agent = MagicMock(spec=LocalGitAgent)
    git_agent.based_on_date = None

    # Act
    create_fork, create_pull_request = resolve_publishing_options(run_args, git_agent)

    # Assert
    assert create_fork is False
    assert create_pull_request is False


def test_resolve_publishing_options_disabled_for_based_on_date(run_args):
    # Arrange
    git_agent = MagicMock()
    git_agent.based_on_date = datetime(2021, 1, 1, tzinfo=timezone.utc)

    # Act
    with patch("osa_tool.run.logger") as mock_logger:
        create_fork, create_pull_request = resolve_publishing_options(run_args, git_agent)

    # Assert
    assert create_fork is False
    assert create_pull_request is False
    warnings = [call.args[0] for call in mock_logger.warning.call_args_list]
    assert any("NO FORK" in message and "NO PULL REQUEST" in message for message in warnings)
