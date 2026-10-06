"""Shared CLI runner for analysis-only paper repository assessment."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Callable

from osa_tool.config.settings import ConfigManager
from osa_tool.operations.analysis.paper_analysis import PaperAnalysisOperation, PaperAnalysisRequest
from osa_tool.tools.focused_cli import configure_focused_tool_logging
from osa_tool.tools.progress import RichStageProgress
from osa_tool.utils.arguments_parser import build_parser_from_yaml
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import delete_created_remote_clone


def add_paper_analysis_arguments(parser: argparse.ArgumentParser, *, main_cli: bool) -> None:
    """Attach mutually exclusive paper inputs and policy overrides to *parser*."""
    group = parser.add_argument_group("paper analysis arguments")
    source = group.add_mutually_exclusive_group(required=False)
    source.add_argument("--paper", type=Path, help="PDF paper to extract through typed paper_claims.")
    source.add_argument("--sections-json", type=Path, help="Parsed PaperSection JSON to extract and verify.")
    source.add_argument("--claims-json", type=Path, help="Typed, legacy, or bare claim JSON to verify.")
    group.add_argument(
        "--paper-claims-prompts-dir",
        type=Path,
        default=None,
        help="Directory of TOML prompt overrides for paper-claim extraction.",
    )
    group.add_argument(
        "--paper-output-dir" if main_cli else "--output-dir",
        dest="paper_output_dir",
        type=Path,
        default=None,
        help=(
            "Directory for paper-analysis artifacts. Configured defaults use a collision-safe clone-name namespace "
            "outside the repository; paths inside the analyzed repository are rejected."
        ),
    )
    quality_group = group.add_mutually_exclusive_group()
    quality_group.add_argument(
        "--include-repository-quality",
        dest="include_repository_quality",
        action="store_true",
        default=None,
        help="Calculate and export the formal 0-100 repository-quality score.",
    )
    quality_group.add_argument(
        "--skip-repository-quality",
        dest="include_repository_quality",
        action="store_false",
        help="Skip formal repository-quality scoring for this run.",
    )
    filter_group = group.add_mutually_exclusive_group()
    filter_group.add_argument(
        "--only-high-medium-verifiability",
        dest="only_high_medium_verifiability",
        action="store_true",
        default=None,
        help="Verify only high- and medium-verifiability claims.",
    )
    filter_group.add_argument(
        "--include-low-verifiability",
        dest="only_high_medium_verifiability",
        action="store_false",
        help="Also verify low or missing-verifiability claims.",
    )
    confidence_group = group.add_mutually_exclusive_group()
    confidence_group.add_argument(
        "--hide-low-confidence",
        dest="hide_low_confidence",
        action="store_true",
        default=None,
        help="Hide low-confidence verification results from the reported rate.",
    )
    confidence_group.add_argument(
        "--include-low-confidence",
        dest="hide_low_confidence",
        action="store_false",
        help="Keep low-confidence verification results in the report and rate.",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the focused paper-analysis parser."""
    parser = build_parser_from_yaml(extra_sections=["settings"])
    parser.description = "Analyze a paper and an OSA-supported repository."
    add_paper_analysis_arguments(parser, main_cli=False)
    return parser


def validate_paper_analysis_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Enforce the source-input contract after a shared parser has run."""
    if not args.repository:
        parser.error("--repository is required")
    provided = sum(item is not None for item in (args.paper, args.sections_json, args.claims_json))
    if provided != 1:
        parser.error("Provide exactly one of --paper, --sections-json, or --claims-json")


def build_request(
    args: argparse.Namespace,
    config_manager: ConfigManager,
    *,
    clone_dir: str | Path | None = None,
) -> PaperAnalysisRequest:
    """Resolve CLI overrides over typed config defaults into the public request contract."""
    settings = config_manager.get_paper_analysis_settings()
    output_dir = args.paper_output_dir or settings.output_dir
    if args.paper_output_dir is None and clone_dir is not None:
        clone_path = Path(clone_dir).resolve()
        output_base = output_dir if output_dir.is_absolute() else clone_path.parent / output_dir
        candidate = (output_base / clone_path.name).resolve()
        if candidate.is_relative_to(clone_path):
            output_base = clone_path.parent / f"{clone_path.name}.osa-artifacts"
        output_dir = output_base / clone_path.name
    return PaperAnalysisRequest(
        repository=str(args.repository),
        paper_path=args.paper,
        sections_path=args.sections_json,
        claims_path=args.claims_json,
        paper_claims_prompts_dir=args.paper_claims_prompts_dir,
        output_dir=output_dir,
        include_repository_quality=(
            settings.include_repository_quality
            if args.include_repository_quality is None
            else args.include_repository_quality
        ),
        only_high_medium_verifiability=(
            settings.only_high_medium_verifiability
            if args.only_high_medium_verifiability is None
            else args.only_high_medium_verifiability
        ),
        hide_low_confidence=(
            settings.hide_low_confidence if args.hide_low_confidence is None else args.hide_low_confidence
        ),
    )


def run_paper_analysis(
    args: argparse.Namespace,
    *,
    config_manager_factory: Callable[[argparse.Namespace], ConfigManager] = ConfigManager,
    git_initializer: Callable[[argparse.Namespace, ConfigManager], tuple[Any, Any]] | None = None,
    operation_factory: Callable[
        [ConfigManager, Any, PaperAnalysisRequest], PaperAnalysisOperation
    ] = PaperAnalysisOperation,
) -> Any:
    """Clone once and run the composed paper-analysis operation without legacy workflows."""
    if git_initializer is None:
        from osa_tool.run import initialize_git_platform

        git_initializer = initialize_git_platform

    config_manager = config_manager_factory(args)
    git_agent, _ = git_initializer(args, config_manager)
    clone_existed_before = Path(git_agent.clone_dir).exists()
    try:
        with RichStageProgress("Preparing paper analysis") as progress:
            logger.info("Paper analysis stage started: Repository clone")
            progress.update("Cloning repository", 0.0)
            git_agent.clone_repository()
            logger.info("Paper analysis stage completed: Repository clone")
            progress.update("Repository cloned", 0.10)
            request = build_request(args, config_manager, clone_dir=git_agent.clone_dir)
            result = operation_factory(config_manager, git_agent, request).run(
                on_progress=lambda message, fraction: progress.update(message, 0.10 + 0.90 * fraction)
            )
        return result
    finally:
        if getattr(args, "delete_dir", False):
            delete_created_remote_clone(
                args.repository,
                git_agent.clone_dir,
                existed_before_clone=clone_existed_before,
            )
