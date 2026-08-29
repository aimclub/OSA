"""Run formal repository-quality scoring without thesis claim analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

from osa_tool.config.settings import ConfigManager
from osa_tool.operations.analysis.repository_quality import RepositoryQualityScorer
from osa_tool.operations.analysis.repository_quality.scoring_engine import RepositoryQualityScoringEngine
from osa_tool.run import initialize_git_platform
from osa_tool.tools.progress import RichStageProgress
from osa_tool.tools.thesis_analysis.cli import configure_focused_tool_logging
from osa_tool.utils.arguments_parser import build_parser_from_yaml
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import delete_created_remote_clone


def build_parser() -> argparse.ArgumentParser:
    """Build the repository-quality-only parser."""
    parser = build_parser_from_yaml(extra_sections=["settings"])
    parser.description = "Calculate OSA's formal repository-quality score."
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help=(
            "Base directory for repository-quality JSON and text reports. The default is a "
            "collision-safe repository_quality sibling of the analyzed clone; paths inside the clone are rejected."
        ),
    )
    return parser


def _is_same_or_nested(path: Path, parent: Path) -> bool:
    """Return whether *path* is the analyzed repository or one of its children."""
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def resolve_output_dir(output_dir: Path | None, *, clone_dir: str | Path, repository: str) -> Path:
    """Resolve a safe report base directory after the repository clone is known."""
    clone_path = Path(clone_dir).resolve()
    base_dir = clone_path.parent / "repository_quality" if output_dir is None else output_dir.expanduser().resolve()
    report_dir_name = RepositoryQualityScoringEngine._sanitize_dir_name(repository)
    report_dir = base_dir / report_dir_name
    if output_dir is None and (_is_same_or_nested(base_dir, clone_path) or _is_same_or_nested(report_dir, clone_path)):
        base_dir = clone_path.parent / f"{clone_path.name}.osa-artifacts"
        report_dir = base_dir / report_dir_name
    if _is_same_or_nested(base_dir, clone_path) or _is_same_or_nested(report_dir, clone_path):
        raise ValueError("The output directory cannot be the analyzed repository or located inside it.")
    return base_dir


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.repository:
        parser.error("--repository is required")
    configure_focused_tool_logging(str(args.repository))
    git_agent = None
    clone_existed_before = False
    try:
        config_manager = ConfigManager(args)
        git_agent, _ = initialize_git_platform(args, config_manager)
        clone_existed_before = Path(git_agent.clone_dir).exists()
        with RichStageProgress("Preparing repository-quality score") as progress:
            logger.info("Repository quality stage started: Repository clone")
            progress.update("Cloning repository", 0.0)
            git_agent.clone_repository()
            logger.info("Repository quality stage completed: Repository clone")
            progress.update("Repository cloned", 0.25)
            progress.update("Calculating formal repository quality", 0.30)
            output_dir = resolve_output_dir(
                args.output_dir,
                clone_dir=git_agent.clone_dir,
                repository=str(config_manager.config.git.repository),
            )
            result = RepositoryQualityScorer(config_manager, git_agent, str(output_dir)).run()
            progress.update("Repository quality artifacts written", 1.0)
    except Exception as exc:
        logger.exception("Repository quality scoring failed: %s", exc)
        return 1
    else:
        print(result["result"]["json_path"])
        return 0
    finally:
        if git_agent is not None and getattr(args, "delete_dir", False):
            delete_created_remote_clone(
                args.repository,
                git_agent.clone_dir,
                existed_before_clone=clone_existed_before,
            )


if __name__ == "__main__":
    raise SystemExit(main())
