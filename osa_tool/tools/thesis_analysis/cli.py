"""Shared CLI runner for analysis-only thesis repository assessment."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any, Callable

from osa_tool.config.settings import ConfigManager
from osa_tool.operations.analysis.thesis_analysis import ThesisAnalysisOperation, ThesisAnalysisRequest
from osa_tool.tools.progress import RichStageProgress
from osa_tool.utils.arguments_parser import build_parser_from_yaml
from osa_tool.utils.logger import logger, setup_logging
from osa_tool.utils.utils import osa_project_root, parse_folder_name


def add_thesis_analysis_arguments(parser: argparse.ArgumentParser, *, main_cli: bool) -> None:
    """Attach mutually exclusive paper inputs and policy overrides to *parser*."""
    group = parser.add_argument_group("thesis analysis arguments")
    source = group.add_mutually_exclusive_group(required=False)
    source.add_argument("--paper", type=Path, help="PDF paper to extract through typed paper_claims.")
    source.add_argument("--claims-json", type=Path, help="Typed, legacy, or bare claim JSON to verify.")
    group.add_argument(
        "--thesis-output-dir" if main_cli else "--output-dir",
        dest="thesis_output_dir",
        type=Path,
        default=None,
        help=(
            "Directory for thesis-analysis artifacts. The configured relative default is created beside the "
            "repository clone; paths inside the analyzed repository are rejected."
        ),
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
    """Build the focused thesis-analysis parser."""
    parser = build_parser_from_yaml(extra_sections=["settings"])
    parser.description = "Analyze a thesis paper and an OSA-supported repository."
    add_thesis_analysis_arguments(parser, main_cli=False)
    return parser


def validate_thesis_analysis_args(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    """Enforce the source-input contract after a shared parser has run."""
    if not args.repository:
        parser.error("--repository is required")
    if (args.paper is None) == (args.claims_json is None):
        parser.error("Provide exactly one of --paper or --claims-json")


def build_request(
    args: argparse.Namespace,
    config_manager: ConfigManager,
    *,
    clone_dir: str | Path | None = None,
) -> ThesisAnalysisRequest:
    """Resolve CLI overrides over typed config defaults into the public request contract."""
    settings = config_manager.get_thesis_analysis_settings()
    output_dir = args.thesis_output_dir or settings.output_dir
    if args.thesis_output_dir is None and clone_dir is not None and not output_dir.is_absolute():
        output_dir = Path(clone_dir).resolve().parent / output_dir
    return ThesisAnalysisRequest(
        repository=str(args.repository),
        paper_path=args.paper,
        claims_path=args.claims_json,
        output_dir=output_dir,
        only_high_medium_verifiability=(
            settings.only_high_medium_verifiability
            if args.only_high_medium_verifiability is None
            else args.only_high_medium_verifiability
        ),
        hide_low_confidence=(
            settings.hide_low_confidence if args.hide_low_confidence is None else args.hide_low_confidence
        ),
    )


def run_thesis_analysis(
    args: argparse.Namespace,
    *,
    config_manager_factory: Callable[[argparse.Namespace], ConfigManager] = ConfigManager,
    git_initializer: Callable[[argparse.Namespace, ConfigManager], tuple[Any, Any]] | None = None,
    operation_factory: Callable[
        [ConfigManager, Any, ThesisAnalysisRequest], ThesisAnalysisOperation
    ] = ThesisAnalysisOperation,
) -> Any:
    """Clone once and run the composed thesis-analysis operation without legacy workflows."""
    if git_initializer is None:
        from osa_tool.run import initialize_git_platform

        git_initializer = initialize_git_platform

    config_manager = config_manager_factory(args)
    git_agent, _ = git_initializer(args, config_manager)
    with RichStageProgress("Preparing thesis analysis") as progress:
        logger.info("Thesis analysis stage started: Repository clone")
        progress.update("Cloning repository", 0.0)
        git_agent.clone_repository()
        logger.info("Thesis analysis stage completed: Repository clone")
        progress.update("Repository cloned", 0.10)
        request = build_request(args, config_manager, clone_dir=git_agent.clone_dir)
        result = operation_factory(config_manager, git_agent, request).run(
            on_progress=lambda message, fraction: progress.update(message, 0.10 + 0.90 * fraction)
        )
    return result


def configure_focused_tool_logging(repository: str) -> None:
    """Configure logs for a focused tool that does not pass through ``osa_tool.run``."""
    logs_dir = os.path.join(os.path.dirname(osa_project_root()), "logs")
    setup_logging(parse_folder_name(repository), logs_dir)
