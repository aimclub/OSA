"""Run formal repository-quality scoring without thesis claim analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

from osa_tool.config.settings import ConfigManager
from osa_tool.operations.analysis.repository_quality import RepositoryQualityScorer
from osa_tool.run import initialize_git_platform
from osa_tool.tools.progress import RichStageProgress
from osa_tool.tools.thesis_analysis.cli import configure_focused_tool_logging
from osa_tool.utils.arguments_parser import build_parser_from_yaml
from osa_tool.utils.logger import logger


def build_parser() -> argparse.ArgumentParser:
    """Build the repository-quality-only parser."""
    parser = build_parser_from_yaml(extra_sections=["settings"])
    parser.description = "Calculate OSA's formal repository-quality score."
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("repository_quality"),
        help="Directory for repository-quality JSON and text reports.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.repository:
        parser.error("--repository is required")
    configure_focused_tool_logging(str(args.repository))
    try:
        config_manager = ConfigManager(args)
        git_agent, _ = initialize_git_platform(args, config_manager)
        with RichStageProgress("Preparing repository-quality score") as progress:
            logger.info("Repository quality stage started: Repository clone")
            progress.update("Cloning repository", 0.0)
            git_agent.clone_repository()
            logger.info("Repository quality stage completed: Repository clone")
            progress.update("Repository cloned", 0.25)
            progress.update("Calculating formal repository quality", 0.30)
            result = RepositoryQualityScorer(config_manager, git_agent, str(args.output_dir)).run()
            progress.update("Repository quality artifacts written", 1.0)
    except Exception as exc:
        logger.exception("Repository quality scoring failed: %s", exc)
        return 1
    print(result["result"]["json_path"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
