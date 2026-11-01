"""Run the focused paper-analysis CLI."""

from __future__ import annotations

from osa_tool.tools.focused_cli import configure_focused_tool_logging
from osa_tool.tools.paper_analysis.cli import (
    build_parser,
    run_paper_analysis,
    validate_paper_analysis_args,
)
from osa_tool.utils.logger import logger


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    validate_paper_analysis_args(parser, args)
    configure_focused_tool_logging(str(args.repository))
    try:
        result = run_paper_analysis(args)
    except Exception as exc:
        logger.exception("Paper analysis failed: %s", exc)
        return 1
    print(result.artifacts.json_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
