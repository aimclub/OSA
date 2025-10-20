import os
import sys
import time

import pandas as pd
from pandas import DataFrame

from osa_tool.analytics.report_maker import ReportGenerator
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.arguments_parser import build_parser_from_yaml
from osa_tool.git_agent.git_agent import GitHubAgent, GitLabAgent, GitverseAgent
from osa_tool.readmegen.context.pypi_status_checker import PyPiPackageInspector
from osa_tool.readmegen.readme_core import ReadmeAgent
from osa_tool.readmegen.utils import format_time
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

    # Create a command line argument parser
    parser = build_parser_from_yaml(extra_sections=["multi-run"])
    args = parser.parse_args()
    table_path = args.table_path

    # Load table containing repository URLs
    df = load_table(table_path)

    # List of repository URLs to process
    repositories = df["repository"].dropna().tolist()

    overall_start = time.time()

    for repo_url in repositories:
        rich_section(f"Processing repository: {repo_url}")

        # Skip repositories already processed
        processed = df.loc[df["repository"] == repo_url, "processed"].any()
        if processed:
            logger.info(f"Skipping already processed repository: {repo_url}")
            continue

        start_time = time.time()

        try:
            # Load configurations and update
            config = load_configuration(
                repo_url=repo_url,
                api=args.api,
                base_url=args.base_url,
                model_name=args.model,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                top_p=args.top_p,
            )

            # Clone the repository
            if "github.com" in repo_url:
                git_agent = GitHubAgent(repo_url)
            elif "gitlab" in args.repository:
                git_agent = GitLabAgent(repo_url)
            elif "gitverse.ru" in args.repository:
                git_agent = GitverseAgent(repo_url)
            else:
                logger.error("Unsupported GIT platform")
                continue

            git_agent.clone_repository()

            # Initialize analytics
            sourcerank = SourceRank(config)

            # Generate reports
            if args.report:
                analytics = ReportGenerator(config, sourcerank, git_agent.metadata)

                # Generate reports directory
                reports_dir = os.path.join(os.path.dirname(args.table_path), "reports")
                os.makedirs(reports_dir, exist_ok=True)

                analytics.output_path = os.path.join(reports_dir, f"{git_agent.metadata.name}_report.pdf")
                analytics.build_pdf()

            # Generate readmes
            if args.readme:
                readme_agent = ReadmeAgent(config, None, args.refine_readme, git_agent.metadata)

                # Generate readmes directory
                readmes_dir = os.path.join(os.path.dirname(args.table_path), "readmes")
                os.makedirs(readmes_dir, exist_ok=True)

                readme_agent.file_to_save = os.path.join(readmes_dir, f"{git_agent.metadata.name}_README.md")
                readme_agent.generate_readme()

            # Get downloads from pepy.tech if exists
            info = PyPiPackageInspector(sourcerank.tree, sourcerank.repo_path).get_info()
            downloads_count = info.get("downloads") if info else ""

            # Update dataframe with repository metadata
            df.loc[df["repository"] == repo_url, "name"] = git_agent.metadata.name
            df.loc[df["repository"] == repo_url, "forks"] = git_agent.metadata.forks_count
            df.loc[df["repository"] == repo_url, "stars"] = git_agent.metadata.stars_count
            df.loc[df["repository"] == repo_url, "downloads"] = downloads_count
            df.loc[df["repository"] == repo_url, "processed"] = True

        finally:
            elapsed_time = time.time() - start_time
            elapsed_formatted = format_time(elapsed_time)
            df.loc[df["repository"] == repo_url, "elapsed_time"] = elapsed_formatted
            logger.info(f"Repository {repo_url} processed in {elapsed_formatted} seconds.")

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

    overall_elapsed = time.time() - overall_start
    rich_section(f"All repositories processed in total time: {format_time(overall_elapsed)}")


def load_table(table_path: str | None) -> DataFrame:
    if table_path:
        if not os.path.isfile(table_path):
            logger.error(f"Table file not found: {table_path}")
            sys.exit(1)

        if not table_path.lower().endswith((".csv", "xlsx")):
            logger.error(f"Table file must be in .csv or .xlsx format: {table_path}")
            sys.exit(1)
    else:
        logger.error(f"Argument '--table-path' is required.")
        sys.exit(1)

    logger.info(f"Reading table from {table_path}")

    # Load the table into a DataFrame
    if table_path.endswith(".csv"):
        df = pd.read_csv(table_path)
    else:
        df = pd.read_excel(table_path)

    if "repository" not in df.columns:
        logger.error("Table must contain a 'repository' column.")
        sys.exit(1)

    # Ensure necessary columns exist
    for col in ["name", "elapsed_time", "forks", "stars", "downloads", "processed"]:
        if col not in df.columns:
            if col == "processed":
                df[col] = False
            else:
                df[col] = None
    return df


if __name__ == "__main__":
    main()
