import logging
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

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
from osa_tool.utils import logger, rich_section, delete_repository, parse_git_url


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

    # Load table containing repository URLs
    df = load_table(args.table_path)
    repositories = df["repository"].dropna().tolist()
    unprocessed = [r for r in repositories if not df.loc[df["repository"] == r, "processed"].any()]

    if not unprocessed:
        rich_section("All repositories already processed.")
        sys.exit(0)

    rich_section(f"Starting parallel processing of {len(unprocessed)} repositories")
    overall_start = time.time()
    results = []

    # Parallel processing
    with ProcessPoolExecutor(max_workers=os.cpu_count() // 2 or 2) as executor:
        future_to_repo = {executor.submit(process_repository, repo, args): repo for repo in unprocessed}
        for future in as_completed(future_to_repo):
            repo_url = future_to_repo[future]
            try:
                result = future.result()
                results.append(result)
                rich_section(f"Done: {repo_url} in {result['elapsed_time']}")
            except Exception as e:
                rich_section(f"Failed: {repo_url} — {e}")

    for res in results:
        repo = res["repository"]
        for key, value in res.items():
            if key in df.columns:
                df.loc[df["repository"] == repo, key] = value

    # Safe table
    if args.table_path.endswith(".csv"):
        df.to_csv(args.table_path, index=False)
    else:
        df.to_excel(args.table_path, index=False)

    total_time = format_time(time.time() - overall_start)
    rich_section(f"All repositories processed in total time: {total_time}")
    rich_section(f"Logs for individual repositories are saved in the {args.table_path + '/logs/'} directory.")


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


def process_repository(repo_url: str, args) -> dict:
    """Process a single repository in a separate process and return its metadata."""
    start_time = time.time()

    # Generate log files for each repo
    _, _, repo_name, _ = parse_git_url(repo_url)
    logs_dir = os.path.join(os.path.dirname(args.table_path), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    log_file = os.path.join(logs_dir, f"{repo_name}.log")

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)

    logger.info(f"Started processing repository: {repo_url}")

    result = {
        "repository": repo_url,
        "name": None,
        "forks": None,
        "stars": None,
        "downloads": None,
        "processed": False,
        "elapsed_time": None,
    }

    try:
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
        elif "gitlab" in repo_url:
            git_agent = GitLabAgent(repo_url)
        elif "gitverse.ru" in repo_url:
            git_agent = GitverseAgent(repo_url)
        else:
            logger.error(f"Unsupported GIT platform: {repo_url}")
            return result

        git_agent.clone_repository()
        sourcerank = SourceRank(config)

        # Generate Report
        if args.report:
            analytics = ReportGenerator(config, sourcerank, git_agent.metadata)
            reports_dir = os.path.join(os.path.dirname(args.table_path), "reports")
            os.makedirs(reports_dir, exist_ok=True)
            analytics.output_path = os.path.join(reports_dir, f"{git_agent.metadata.name}_report.pdf")
            analytics.build_pdf()

        # Generate README
        if args.readme:
            readme_agent = ReadmeAgent(config, None, args.refine_readme, git_agent.metadata)
            readmes_dir = os.path.join(os.path.dirname(args.table_path), "readmes")
            os.makedirs(readmes_dir, exist_ok=True)
            readme_agent.file_to_save = os.path.join(readmes_dir, f"{git_agent.metadata.name}_README.md")
            readme_agent.generate_readme()

        info = PyPiPackageInspector(sourcerank.tree, sourcerank.repo_path).get_info()
        downloads_count = info.get("downloads") if info else ""

        # Get results
        result.update(
            {
                "name": git_agent.metadata.name,
                "forks": git_agent.metadata.forks_count,
                "stars": git_agent.metadata.stars_count,
                "downloads": downloads_count,
                "processed": True,
            }
        )

    except Exception as e:
        logger.error(f"Error while processing {repo_url}: {e}")

    finally:
        elapsed = time.time() - start_time
        result["elapsed_time"] = format_time(elapsed)
        logger.info(f"Finished repository {repo_url} in {format_time(elapsed)}")
        delete_repository(repo_url)

    return result


if __name__ == "__main__":
    main()
