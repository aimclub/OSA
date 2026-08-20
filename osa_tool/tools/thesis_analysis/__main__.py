"""Run the thesis-analysis operation without changing OSA's legacy scheduler CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from osa_tool.config.settings import ConfigManager
from osa_tool.operations.analysis.thesis_analysis import ThesisAnalysisOperation, ThesisAnalysisRequest
from osa_tool.run import initialize_git_platform
from osa_tool.utils.arguments_parser import build_parser_from_yaml


def build_parser() -> argparse.ArgumentParser:
    parser = build_parser_from_yaml(extra_sections=["settings"])
    parser.description = "Analyze a thesis paper and an OSA-supported repository."
    group = parser.add_argument_group("thesis analysis arguments")
    source = group.add_mutually_exclusive_group(required=True)
    source.add_argument("--paper", type=Path, help="PDF paper to extract through OSA paper_claims.")
    source.add_argument("--claims-json", type=Path, help="Typed, legacy, or bare claim JSON to verify.")
    group.add_argument("--output-dir", type=Path, default=Path("thesis_analysis"))
    group.add_argument(
        "--include-low-verifiability",
        action="store_true",
        help="Verify low, missing, and invalid-verifiability claims too.",
    )
    group.add_argument(
        "--include-low-confidence",
        action="store_true",
        help="Keep low-confidence verification results in the report and rate.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if not args.repository:
        parser.error("--repository is required")
    config_manager = ConfigManager(args)
    git_agent, _ = initialize_git_platform(args, config_manager)
    git_agent.clone_repository()
    result = ThesisAnalysisOperation(
        config_manager,
        git_agent,
        ThesisAnalysisRequest(
            repository=str(args.repository),
            paper_path=args.paper,
            claims_path=args.claims_json,
            output_dir=args.output_dir,
            only_high_medium_verifiability=not args.include_low_verifiability,
            hide_low_confidence=not args.include_low_confidence,
        ),
    ).run()
    print(result.artifacts.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
