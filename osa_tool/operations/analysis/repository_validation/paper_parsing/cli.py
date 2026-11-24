"""Standalone paper parsing and document graph operations for the OSA CLI."""

from argparse import Namespace
from pathlib import Path

from osa_tool.config.settings import ConfigManager
from osa_tool.operations.analysis.repository_validation.paper_parsing.doc_graph import run_graph_building


def run_paper_parsing(args: Namespace) -> Path:
    source = Path(args.parse_paper or args.build_paper_graph)
    destination = Path(args.paper_parsing_output_dir or Path("artifacts", "paper-parsing", source.stem))
    graph_path = destination / "graph.json"
    if args.build_paper_graph:
        run_graph_building(source, graph_path)
        return graph_path

    if not source.is_file():
        raise FileNotFoundError(f"PDF file does not exist: {source}")
    try:
        from osa_tool.operations.analysis.repository_validation.paper_parsing.structured_parser import (
            StructuredPaperParser,
        )
    except ImportError as exc:
        raise RuntimeError(
            f'PDF parsing requires the paper-parsing extra. Run pip install "osa_tool[paper-parsing]". ({exc})'
        ) from exc

    settings = ConfigManager(args).get_model_settings("paper_parsing")
    parser = StructuredPaperParser.from_model_settings(source, settings)
    parser.export(parser.parse(), destination, include_report=True)
    return graph_path
