import os
import sys
import time
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Callable

from osa_tool.config.settings import ConfigManager
from osa_tool.operations.analysis.notebook_report.report_maker import NotebookReportGenerator
from osa_tool.core.git.git_agent import (
    GitHubAgent,
    GitLabAgent,
    GitverseAgent,
    SourceCraftAgent,
    GitAgent,
    LocalGitAgent,
)
from osa_tool.core.models.task import TaskStatus
from osa_tool.operations.analysis.repository_report.report_maker import ReportGenerator, WhatHasBeenDoneReportGenerator
from osa_tool.operations.codebase.directory_translation.dirs_and_files_translator import RepositoryStructureTranslator
from osa_tool.operations.codebase.docstring_generation.docstring_generation import DocstringsGenerator
from osa_tool.operations.codebase.notebook_conversion.notebook_converter import NotebookConverter
from osa_tool.operations.codebase.organization.organize import RepoOrganizer
from osa_tool.operations.codebase.requirements_generation.requirements_generation import RequirementsGenerator
from osa_tool.operations.docs.about_generation.about_generator import AboutGenerator
from osa_tool.operations.docs.community_docs_generation.docs_run import generate_documentation
from osa_tool.operations.docs.community_docs_generation.license_generation import LicenseCompiler
from osa_tool.operations.docs.readme_generation.readme_agent import ReadmeAgent
from osa_tool.operations.docs.readme_translation.readme_translator import ReadmeTranslator
from osa_tool.scheduler.plan import FAILURE_STATUSES, Plan
from osa_tool.scheduler.scheduler import ModeScheduler
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.scheduler.workflow_manager import (
    GitHubWorkflowManager,
    GitLabWorkflowManager,
    GitverseWorkflowManager,
    SourceCraftWorkflowManager,
    WorkflowGenerationError,
    WorkflowManager,
)
from osa_tool.utils.arguments_parser import apply_argument_descriptions_from_yaml, build_parser_from_yaml
from osa_tool.utils.logger import logger, setup_logging
from osa_tool.utils.utils import (
    delete_created_remote_clone,
    prepare_local_output_repository,
    osa_project_root,
    parse_folder_name,
    rich_section,
    switch_to_output_directory,
    format_time,
)


def main():
    """Main function to generate a README.md file for a Git repository.

    Handles command-line arguments, clones the repository, creates and checks out a branch,
    generates the README.md file, and commits and pushes the changes.
    """

    # Create a command line argument parser
    parser = build_parser_from_yaml(extra_sections=["settings", "arguments", "workflow"])
    from osa_tool.tools.paper_analysis.cli import add_paper_analysis_arguments

    add_paper_analysis_arguments(parser, main_cli=True)
    # Keep public help text in the shared argument metadata.
    apply_argument_descriptions_from_yaml(parser, ["paper_analysis_cli"])
    args = parser.parse_args()

    if args.paper_analysis:
        from osa_tool.tools.focused_cli import configure_focused_tool_logging
        from osa_tool.tools.paper_analysis.cli import (
            run_paper_analysis,
            validate_paper_analysis_args,
        )

        validate_paper_analysis_args(parser, args)
        configure_focused_tool_logging(str(args.repository))
        try:
            result = run_paper_analysis(args)
        except Exception as exc:
            logger.exception("Paper analysis failed: %s", exc)
            return 1
        else:
            print(result.artifacts.json_path)
            return 0
    start_time = time.time()
    plan = None
    clone_dir = None
    try:
        logs_dir = os.path.join(os.path.dirname(osa_project_root()), "logs")
        setup_logging(parse_folder_name(args.repository), logs_dir)
        # Switch to output directory if present
        if args.output:
            output_path = switch_to_output_directory(args.output)
            if os.path.isdir(args.repository):
                args.repository = str(prepare_local_output_repository(args.repository, output_path))

        # Load configurations and update
        config_manager = ConfigManager(args)

        # Initialize Git agent and Workflow Manager for used platform, perform operations
        git_agent, workflow_manager = initialize_git_platform(args, config_manager)

        create_fork, create_pull_request = resolve_publishing_options(args, git_agent)

        if create_fork:
            git_agent.star_repository()
            git_agent.create_fork()
        clone_dir = Path(git_agent.clone_dir)
        existed_before_clone = clone_dir.exists() or clone_dir.is_symlink()
        git_agent.clone_repository()
        # Refresh CI/CD state from the freshly cloned repo.
        # WorkflowManager.__init__ already ran before clone, so it may have read
        # stale workflow files left over from a previous local run.
        workflow_manager.refresh_after_clone()

        # Initialize ModeScheduler
        sourcerank = SourceRank(config_manager)
        scheduler = ModeScheduler(config_manager, sourcerank, args, workflow_manager, git_agent.metadata)
        plan = scheduler.plan
        artefacts_language = plan.get("artefacts_language")

        # Scorecard results are rendered inside the analysis report, so --scorecard
        # has no effect on its own; enable report generation when only it is set.
        run_report = bool(plan.get("report") or plan.get("scorecard"))
        if plan.get("scorecard") and not plan.get("report"):
            logger.info("Scorecard requested without --report; enabling report generation to render it.")

        if create_fork:
            git_agent.create_and_checkout_branch()

        # Repository Analysis Report generation
        # Measure the repository before applying any changes.
        if run_report:
            rich_section("Report generation")
            _run_plan_operation(
                plan,
                "report",
                lambda: ReportGenerator(
                    config_manager, git_agent, False, artefacts_language, run_scorecard=plan.get("scorecard")
                ).run(),
            )

        notebook_report = plan.get("notebook_report")
        if notebook_report is not None:
            rich_section("Notebook report generation")
            _run_plan_operation(
                plan,
                "notebook_report",
                lambda: NotebookReportGenerator(
                    config_manager,
                    git_agent,
                    False,
                    notebook_report,
                    target_language=artefacts_language,
                ).run(),
            )

        # .ipynb to .py conversion
        notebook = plan.get("convert_notebooks")
        if notebook is not None:
            rich_section("Jupyter notebooks conversion")
            _run_plan_operation(
                plan,
                "convert_notebooks",
                lambda: NotebookConverter(config_manager, notebook).convert_notebooks(),
            )

        # Auto translating names of directories
        if plan.get("translate_dirs"):
            rich_section("Directory and file translation")
            _run_plan_operation(
                plan,
                "translate_dirs",
                lambda: RepositoryStructureTranslator(config_manager).rename_directories_and_files(),
            )

        # Docstring generation
        if plan.get("docstring"):
            rich_section("Docstrings generation")
            _run_plan_operation(
                plan,
                "docstring",
                lambda: DocstringsGenerator(
                    config_manager=config_manager,
                    ignore_list=args.ignore_list,
                    incremental=args.incremental,
                    target_files=args.target_files,
                ).run(),
            )

        # License compiling
        if license_type := plan.get("ensure_license"):
            rich_section("License generation")
            _run_plan_operation(
                plan,
                "ensure_license",
                lambda: LicenseCompiler(config_manager, git_agent.metadata, license_type).run(),
            )

        # Generate community documentation
        if plan.get("community_docs"):
            rich_section("Community docs generation")
            _run_plan_operation(
                plan,
                "community_docs",
                lambda: generate_documentation(config_manager, git_agent.metadata),
            )

        # Requirements generation
        if plan.get("requirements"):
            rich_section("Requirements generation")
            _run_plan_operation(
                plan,
                "requirements",
                lambda: RequirementsGenerator(config_manager).generate(),
            )

        # Readme generation
        if plan.get("readme"):
            rich_section("README generation")
            _run_plan_operation(
                plan,
                "readme",
                lambda: ReadmeAgent(config_manager, git_agent.metadata, plan.get("attachment")).generate_readme(),
            )

        # Readme translation
        translate_readme = plan.get("translate_readme")
        if translate_readme:
            rich_section("README translation")
            _run_plan_operation(
                plan,
                "translate_readme",
                lambda: ReadmeTranslator(config_manager, git_agent.metadata, translate_readme).translate_readme(),
            )

        # About section generation
        if plan.get("about"):
            rich_section("About Section generation")
            _run_plan_operation(
                plan,
                "about",
                lambda: _generate_about(config_manager, git_agent),
            )

        # Generate platform-specified CI/CD files
        if plan.get("generate_workflows"):
            rich_section("Workflows generation")
            _run_plan_operation(
                plan, "generate_workflows", lambda: _generate_workflows(config_manager, workflow_manager, plan)
            )

        # Organize repository by adding 'tests' and 'examples' directories if they aren't exist
        if plan.get("organize"):
            rich_section("Repository organization")
            _run_plan_operation(
                plan,
                "organize",
                lambda: RepoOrganizer(config_manager, git_agent.metadata).organize(),
            )

        operation_keys = tuple(plan.results)
        has_output = any(plan.tasks[key] in {TaskStatus.COMPLETED, TaskStatus.PARTIAL} for key in operation_keys)
        allow_publish = create_fork and not any(
            plan.tasks[key] in FAILURE_STATUSES for key in operation_keys if key not in {"report", "notebook_report"}
        )
        about = (plan.results.get("about") or {}).get("result") or {}
        if (message := about.get("message")) and (not allow_publish or not create_pull_request):
            logger.info("About section:\n%s", message)
        with git_agent.report_upload_session() if allow_publish else nullcontext():
            if allow_publish:
                _publish_changes(plan, git_agent, create_pull_request, about)
            elif create_fork:
                plan.complete_operation("publish", {"status": TaskStatus.SKIPPED})
                logger.warning("Skipping publication because an operation that changes the repository failed.")

            if run_report:
                _run_plan_operation(
                    plan,
                    "work_summary",
                    lambda: WhatHasBeenDoneReportGenerator(
                        config_manager, git_agent, False, plan, artefacts_language, run_scorecard=plan.get("scorecard")
                    ).run(),
                )
                if allow_publish:
                    _upload_generated_report(plan, git_agent, "work_summary")

        if plan.get("delete_dir"):
            if _has_failures(plan):
                plan.complete_operation("delete_dir", {"status": TaskStatus.SKIPPED})
            else:
                _run_plan_operation(
                    plan, "delete_dir", lambda: _clean_clone(args.repository, clone_dir, existed_before_clone)
                )

        exit_code = (3 if has_output else 1) if _has_failures(plan) else 0
    except Exception as e:
        if plan is None:
            plan = Plan({})
        plan.complete_operation("run", {"result": {"error": str(e)}})
        logger.error("Run failed: %s", Plan.brief_reason(str(e)), exc_info=not args.web_mode)
        exit_code = 1

    _print_run_summary(plan, exit_code, start_time)
    if exit_code and clone_dir is not None and clone_dir.exists():
        logger.info("Working copy retained at %s", clone_dir)
    sys.exit(exit_code)


def resolve_publishing_options(args, git_agent: GitAgent) -> tuple[bool, bool]:
    """Decides whether the results of a run may be published back to the repository.

    Args:
        args: The parsed command line arguments.
        git_agent: The Git agent initialized for the processed repository.

    Returns:
        A tuple of the `create_fork` and `create_pull_request` flags.
    """
    create_fork = not args.no_fork
    create_pull_request = not args.no_pull_request

    if isinstance(git_agent, LocalGitAgent):
        create_fork = False
        create_pull_request = False

    # A dated run analyses a historical version of the repository,
    # so publishing its outdated tree back to the project has to be suppressed.
    if git_agent.based_on_date and (create_fork or create_pull_request):
        logger.warning(
            f"'--based-on-date' is set: the repository is analysed as of "
            f"{git_agent.based_on_date.date()}, "
            "NO FORK and NO PULL REQUEST options are forced for this run, "
            "so none of the results will be published to the repository."
        )
        create_fork = False
        create_pull_request = False

    return create_fork, create_pull_request


def initialize_git_platform(args, config_manager: ConfigManager) -> tuple[GitAgent, WorkflowManager]:
    if (os.getenv("GITHUB_ACTIONS") is not None) and (os.getenv("GITHUB_ACTIONS").lower() == "true"):
        target_branch = args.branch
    else:
        target_branch = getattr(config_manager.config.git, "osa_branch_name", "osa_tool")

    based_on_date = config_manager.config.git.based_on_date

    if os.path.isdir(args.repository):
        git_agent = LocalGitAgent(args.repository, args.branch, author=args.author, based_on_date=based_on_date)
        workflow_manager = GitHubWorkflowManager(args.repository, git_agent.metadata, args)
    elif "github.com" in args.repository:
        git_agent = GitHubAgent(
            args.repository,
            repo_branch_name=args.branch,
            branch_name=target_branch,
            author=args.author,
            based_on_date=based_on_date,
        )
        workflow_manager = GitHubWorkflowManager(args.repository, git_agent.metadata, args)
    elif "gitlab." in args.repository:
        git_agent = GitLabAgent(
            args.repository,
            repo_branch_name=args.branch,
            branch_name=target_branch,
            author=args.author,
            based_on_date=based_on_date,
        )
        workflow_manager = GitLabWorkflowManager(args.repository, git_agent.metadata, args)
    elif "gitverse.ru" in args.repository:
        git_agent = GitverseAgent(
            args.repository,
            repo_branch_name=args.branch,
            branch_name=target_branch,
            author=args.author,
            based_on_date=based_on_date,
        )
        workflow_manager = GitverseWorkflowManager(args.repository, git_agent.metadata, args)
    elif "sourcecraft.dev" in args.repository:
        git_agent = SourceCraftAgent(args.repository, args.branch, author=args.author, based_on_date=based_on_date)
        workflow_manager = SourceCraftWorkflowManager(args.repository, git_agent.metadata, args)
    else:
        raise ValueError(f"Cannot initialize Git Agent and Workflow Manager for this platform: {args.repository}")

    return git_agent, workflow_manager


def _run_plan_operation(plan: Plan, task_key: str, call: Callable[[], Any]) -> TaskStatus:
    """Isolate an operation, including executor initialization and result handling."""
    plan.mark_started(task_key)
    try:
        return plan.complete_operation(task_key, call())
    except Exception as e:
        return plan.complete_operation(task_key, {"result": {"error": Plan.brief_reason(str(e)) or type(e).__name__}})


def _generate_about(config_manager: ConfigManager, git_agent: GitAgent) -> dict:
    generator = AboutGenerator(config_manager, git_agent)
    outcome = generator.generate_about_content()
    content = outcome.get("result")
    if content and any(content.values()):
        outcome["result"] = {"content": content, "message": generator.get_about_section_message()}
    else:
        outcome["result"] = None
    return outcome


def _generate_workflows(config_manager: ConfigManager, workflow_manager: WorkflowManager, plan: Plan) -> dict:
    workflow_manager.update_workflow_config(config_manager, plan)
    try:
        files = workflow_manager.generate_workflow_files(config_manager)
    except WorkflowGenerationError as exc:
        return {"status": TaskStatus.PARTIAL, "result": {"error": str(exc), "files": exc.files}}
    if not files:
        return {"status": TaskStatus.SKIPPED}
    return {"result": {"files": files}}


def _upload_generated_report(plan: Plan, git_agent: GitAgent, task: str) -> None:
    report = (plan.results.get(task) or {}).get("result")
    if isinstance(report, dict) and report.get("path"):
        _run_plan_operation(plan, f"upload_{task}", lambda: git_agent.upload_report(report["report"], report["path"]))


def _publish_changes(plan: Plan, git_agent: GitAgent, create_pull_request: bool, about: dict) -> None:
    rich_section("Publishing changes")
    if "content" in about:

        def publish_about() -> dict:
            if git_agent.update_about_section(about["content"], strict=True) is False:
                return {"status": TaskStatus.SKIPPED}
            return {"status": TaskStatus.COMPLETED}

        _run_plan_operation(plan, "publish_about", publish_about)

    def push_changes() -> dict:
        if git_agent.commit_and_push_changes(force=True):
            return {"result": True}
        return {"status": TaskStatus.SKIPPED, "result": False}

    def publish_pull_request() -> dict:
        result = git_agent.create_pull_request(
            body=about.get("message", ""), changes=plan.results["publish_push"]["result"], strict=True
        )
        if result is False:
            return {"status": TaskStatus.SKIPPED}
        return {"result": result}

    if create_pull_request:
        _run_plan_operation(plan, "publish_push", push_changes)
    for task in ("report", "notebook_report"):
        _upload_generated_report(plan, git_agent, task)
    if create_pull_request:
        if plan.tasks["publish_push"] in FAILURE_STATUSES:
            plan.complete_operation("publish_pr", {"status": TaskStatus.SKIPPED})
        else:
            _run_plan_operation(plan, "publish_pr", publish_pull_request)


def _clean_clone(repository: str, clone_dir: Path, existed_before_clone: bool) -> dict:
    if clone_dir.is_symlink() or not delete_created_remote_clone(
        repository, clone_dir, existed_before_clone=existed_before_clone
    ):
        return {"status": TaskStatus.SKIPPED}
    if clone_dir.exists():
        raise OSError(f"Could not remove the working copy at {clone_dir}")
    return {"status": TaskStatus.COMPLETED}


def _has_failures(plan: Plan) -> bool:
    return any(plan.tasks[task] in FAILURE_STATUSES for task in plan.results)


def _print_run_summary(plan: Plan, exit_code: int, start_time: float) -> None:
    rich_section("Run summary")
    for task, status, reasons in plan.operation_rows():
        log = logger.error if status in FAILURE_STATUSES else logger.info
        log("%s: %s", task, status.value)
        for reason in reasons:
            log("  %s", reason)
    message = {0: "Run completed successfully", 1: "Run failed", 3: "Run completed with partial results"}[exit_code]
    rich_section(f"{message} in {format_time(time.time() - start_time)}")


def _main_entrypoint() -> None:
    """Exit a module invocation with the status returned by :func:`main`."""
    raise SystemExit(main())


if __name__ == "__main__":
    _main_entrypoint()
