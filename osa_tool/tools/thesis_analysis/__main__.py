"""Run the focused thesis-analysis CLI."""

from __future__ import annotations

from osa_tool.tools.thesis_analysis.cli import (
    build_parser,
    configure_focused_tool_logging,
    run_thesis_analysis,
    validate_thesis_analysis_args,
)
from osa_tool.utils.logger import logger


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    validate_thesis_analysis_args(parser, args)
    configure_focused_tool_logging(str(args.repository))
    try:
        result = run_thesis_analysis(args)
    except Exception as exc:
        logger.exception("Thesis analysis failed: %s", exc)
        return 1
    print(result.artifacts.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
