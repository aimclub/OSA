import argparse
import os
import sys

import pandas as pd

from osa_tool.analytics.report_maker import ReportGenerator
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.git_agent.git_agent import GitAgent
from osa_tool.readmegen.context.pypi_status_checker import PyPiPackageInspector
from osa_tool.run import load_configuration
from osa_tool.utils import logger, rich_section, delete_repository


def main():
    """
    Main entry point for the pipeline.

    Reads a table (CSV or Excel) containing repository URLs,
    processes each repository by cloning, analyzing, and generating a PDF report,
    and updates the table with repository metadata such as name, forks count, stars count,
    and marks processed repositories to avoid duplication.

    If the 'reports' directory next to the table does not exist, it will be created.

    The table file is overwritten after processing each repository to save progress.
    """
    args = parse_arguments()

    if args.table_path:
        if not os.path.isfile(args.table_path):
            logger.error(f"Table file not found: {args.table_path}")
            sys.exit(1)

        if not args.table_path.lower().endswith((".csv", "xlsx")):
            logger.error(f"Table file must be in .csv or .xlsx format: {args.table_path}")
            sys.exit(1)

    logger.info(f"Reading table from {args.table_path}")

    # Load the table into a DataFrame
    if args.table_path.endswith(".csv"):
        df = pd.read_csv(args.table_path)
    else:
        df = pd.read_excel(args.table_path)

    if "repository" not in df.columns:
        logger.error("Table must contain a 'repository' column.")

    # Ensure necessary columns exist; add if missing
    for col in ["name", "forks", "stars", "downloads", "processed"]:
        if col not in df.columns:
            if col == "processed":
                df[col] = False
            else:
                df[col] = None

    # List of repository URLs to process
    repositories = df["repository"].dropna().tolist()

    reports_dir = os.path.join(os.path.dirname(args.table_path), "reports")
    os.makedirs(reports_dir, exist_ok=True)

    for repo_url in repositories:
        rich_section(f"Processing repository: {repo_url}")

        # Skip repositories already processed
        processed = df.loc[df["repository"] == repo_url, "processed"].any()
        if processed:
            logger.info(f"Skipping already processed repository: {repo_url}")
            continue

        config = load_configuration(
            repo_url=repo_url,
            api=args.api,
            base_url=args.base_url,
            model_name=args.model,
        )

        # Clone the repository
        github_agent = GitAgent(repo_url)
        github_agent.clone_repository()

        # Initialize analytics and generate report
        sourcerank = SourceRank(config)
        analytics = ReportGenerator(config, sourcerank)
        analytics.output_path = os.path.join(reports_dir, f"{analytics.metadata.name}_report.pdf")
        analytics.build_pdf()

        # Get downloads from pepy.tech if exists
        info = PyPiPackageInspector(sourcerank.tree, sourcerank.repo_path).get_info()
        downloads_count = info.get("downloads") if info else ""

        # Update dataframe with repository metadata
        df.loc[df["repository"] == repo_url, "name"] = analytics.metadata.name
        df.loc[df["repository"] == repo_url, "forks"] = analytics.metadata.forks_count
        df.loc[df["repository"] == repo_url, "stars"] = analytics.metadata.stars_count
        df.loc[df["repository"] == repo_url, "downloads"] = downloads_count
        df.loc[df["repository"] == repo_url, "processed"] = True

        # Save updated table after processing each repository
        if os.path.exists(args.table_path):
            try:
                os.rename(args.table_path, args.table_path)  # Attempt to rename to itself as a lock check
            except OSError:
                logger.error(f"Cannot access {args.table_path}. Is it open in another program?")
                sys.exit(1)

        if args.table_path.endswith(".csv"):
            df.to_csv(args.table_path, index=False)
        else:
            df.to_excel(args.table_path, index=False)

        # Delete repository's directory after processing
        delete_repository(repo_url)

        logger.info(f"Finished processing: {repo_url}")


def parse_arguments() -> argparse.Namespace:
    """
    Parses command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments including:
          - table_path: path to input table file (.csv or .xlsx)
          - api: choice of LLM API provider ("itmo", "openai", "ollama")
          - base_url: base URL of the API provider
          - model: LLM model name to use
    """
    parser = argparse.ArgumentParser(description="Pipeline for processing repositories and generating reports")

    parser.add_argument(
        "--table-path", type=str, help="Path to an Excel (.xlsx) or CSV file containing tabular data.", required=True
    )
    parser.add_argument(
        "--api", type=str, choices=["itmo", "openai", "ollama"], help="LLM API service provider.", default="itmo"
    )
    parser.add_argument(
        "--base-url",
        type=str,
        help="URL of the provider compatible with API OpenAI.",
        default="https://api.openai.com/v1",
    )
    parser.add_argument(
        "--model",
        type=str,
        help=(
            "Specific LLM model to use.\n"
            "See:\n"
            "1. https://vsegpt.ru/Docs/Models\n"
            "2. https://platform.openai.com/docs/models\n"
            "3. https://ollama.com/library"
        ),
        default="gpt-3.5-turbo",
    )
    return parser.parse_args()


if __name__ == "__main__":
    main()
