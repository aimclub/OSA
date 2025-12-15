import asyncio
import logging
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd
from pandas import DataFrame

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.analytics.report_maker import ReportGenerator
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.git_agent.git_agent import GitHubAgent, GitLabAgent, GitverseAgent
from osa_tool.readmegen.context.pypi_status_checker import PyPiPackageInspector
from osa_tool.readmegen.readme_core import ReadmeAgent
from osa_tool.readmegen.utils import format_time
from osa_tool.run import generate_docstrings, load_configuration
from osa_tool.utils.arguments_parser import build_parser_from_yaml
from osa_tool.utils.prompts_builder import PromptLoader
from osa_tool.utils.utils import logger, rich_section, parse_git_url, delete_repository


# === Stage 1: Generate report and README asynchronously ===


async def generate_report(
    config: ConfigLoader, sourcerank: SourceRank, prompts: PromptLoader, metadata: RepositoryMetadata, args
) -> None:
    """Async wrapper for generating PDF report."""
    reports_dir = os.path.join(os.path.dirname(args.table_path), "reports")
    os.makedirs(reports_dir, exist_ok=True)

    report_gen = ReportGenerator(config, sourcerank, prompts, metadata)
    report_gen.output_path = os.path.join(reports_dir, f"{metadata.name}_report.pdf")

    await asyncio.to_thread(report_gen.build_pdf)


async def generate_readme(config: ConfigLoader, prompts: PromptLoader, metadata: RepositoryMetadata, args) -> None:
    """Async wrapper for generating README."""
    readmes_dir = os.path.join(os.path.dirname(args.table_path), "readmes")
    os.makedirs(readmes_dir, exist_ok=True)

    readme_agent = ReadmeAgent(config, prompts, None, args.refine_readme, metadata)
    readme_agent.file_to_save = os.path.join(readmes_dir, f"{metadata.name}_README.md")

    await asyncio.to_thread(readme_agent.generate_readme)


async def run_async_tasks(config: ConfigLoader, sourcerank: SourceRank, prompts: PromptLoader, git_agent, args):
    """Run report and readme generation concurrently inside a process."""
    tasks = []

    if args.report:
        tasks.append(asyncio.create_task(generate_report(config, sourcerank, prompts, git_agent.metadata, args)))
    if args.readme:
        tasks.append(asyncio.create_task(generate_readme(config, prompts, git_agent.metadata, args)))
    if tasks:
        await asyncio.gather(*tasks)


def process_repository_stage1(repo_url: str, prompts: PromptLoader, args) -> dict:
    """
    Stage 1: Clone repository, generate report and README asynchronously.
    This stage runs in multiple processes concurrently.
    """
    stage_start = time.time()

    # Setup working directories
    repos_dir = os.path.join(os.path.dirname(args.table_path), "repositories")
    logs_dir = os.path.join(os.path.dirname(args.table_path), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(repos_dir, exist_ok=True)
    os.chdir(repos_dir)

    # Setup logging per repository
    _, _, repo_name, _ = parse_git_url(repo_url)
    log_file = os.path.join(logs_dir, f"{repo_name}.log")
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)
    logger.info(f"Started processing repository: {repo_url}")

    result = {
        "repository": repo_url,
        "name": "",
        "forks": None,
        "stars": None,
        "downloads": None,
        "processed_stage1": False,
        "processed_docstring": False,
        "stage1_time": 0.0,
        "stage1_time_str": "",
    }

    try:
        args.repository = repo_url
        config = load_configuration(args)

        # Choose GIT agent based on platform
        if "github.com" in repo_url:
            git_agent = GitHubAgent(repo_url)
        elif "gitlab" in repo_url:
            git_agent = GitLabAgent(repo_url)
        elif "gitverse.ru" in repo_url:
            git_agent = GitverseAgent(repo_url)
        else:
            logger.error(f"Unsupported GIT platform: {repo_url}")
            return result

        # Clone repository
        git_agent.clone_repository()
        sourcerank = SourceRank(config)

        # Run async stage (report + readme)
        asyncio.run(run_async_tasks(config, sourcerank, prompts, git_agent, args))

        # Collect PyPi info
        info = PyPiPackageInspector(sourcerank.tree, sourcerank.repo_path).get_info()
        downloads_count = info.get("downloads") if info else ""

        stage_elapsed = time.time() - stage_start

        # Update results
        result.update(
            {
                "name": git_agent.metadata.name,
                "forks": git_agent.metadata.forks_count,
                "stars": git_agent.metadata.stars_count,
                "downloads": downloads_count,
                "stage1_time": stage_elapsed,
                "stage1_time_str": format_time(stage_elapsed),
                "processed_stage1": True,
            }
        )

        logger.info(f"Stage 1 completed successfully in {result['stage1_time_str']}")

    except Exception as e:
        logger.error(f"Error during Stage 1 for {repo_url}: {e}")

    finally:
        logger.removeHandler(file_handler)

        # Remove cloned repo if docstring generation not required
        if not args.docstring:
            delete_repository(repo_url)

    return result


# === Stage 2: Sequential docstring generation ===


def process_docstrings_for_repo(repo_url: str, args, df: DataFrame) -> None:
    """
    Stage 2: Generate docstrings sequentially for each repository.
    After processing each repository, immediately update the table file.
    """
    stage_start = time.time()

    # Setup working directories
    repos_dir = os.path.join(os.path.dirname(args.table_path), "repositories")
    logs_dir = os.path.join(os.path.dirname(args.table_path), "logs")
    os.chdir(repos_dir)

    # Setup logging per repository
    _, _, repo_name, _ = parse_git_url(repo_url)
    log_file = os.path.join(logs_dir, f"{repo_name}.log")

    # Append to existing log file
    file_handler = logging.FileHandler(log_file, encoding="utf-8", mode="a")
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)

    logger.info(f"Starting docstring generation for {repo_url}")

    try:
        args.repository = repo_url
        config = load_configuration(args)

        # Generate docstrings
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            generate_docstrings(config, loop, args.ignore_list)
        finally:
            loop.close()

        stage_elapsed = time.time() - stage_start
        stage_elapsed_str = format_time(stage_elapsed)

        df.loc[df["repository"] == repo_url, "stage2_time"] = stage_elapsed
        df.loc[df["repository"] == repo_url, "stage2_time_str"] = stage_elapsed_str
        df.loc[df["repository"] == repo_url, "processed_docstring"] = True

        # Save progress immediately to avoid data loss
        try:
            if args.table_path.endswith(".csv"):
                df.to_csv(args.table_path, index=False)
            else:
                df.to_excel(args.table_path, index=False)
        except PermissionError:
            logger.warning(
                f"Cannot save table '{args.table_path}'. "
                "If you know you have access to this file, "
                "try to close applications that are using it."
            )

        logger.info(f"Finished docstrings for {repo_url} in {stage_elapsed_str}")

    except Exception as e:
        logger.error(f"Error generating docstrings for {repo_url}: {e}")

    finally:
        logger.removeHandler(file_handler)


# === Table management ===


def load_table(table_path: str | None) -> DataFrame:
    """Load repository table."""
    if not table_path:
        logger.error(f"Argument '--table-path' is required.")
        sys.exit(1)
    if not os.path.isfile(table_path):
        logger.error(f"Table file not found: {table_path}")
        sys.exit(1)
    if not table_path.lower().endswith((".csv", ".xlsx")):
        logger.error(f"Table must be .csv or .xlsx format: {table_path}")
        sys.exit(1)

    logger.info(f"Loading repository table from {table_path}")

    df = pd.read_csv(table_path) if table_path.endswith(".csv") else pd.read_excel(table_path)

    if "repository" not in df.columns:
        logger.error("Table must contain a 'repository' column.")
        sys.exit(1)

    for col in [
        "name",
        "forks",
        "stars",
        "downloads",
        "processed_stage1",
        "processed_docstring",
        "stage1_time",
        "stage1_time_str",
        "stage2_time",
        "stage2_time_str",
    ]:
        if col not in df.columns:
            if col in ["processed_stage1", "processed_docstring"]:
                df[col] = False
            elif col in ["name", "stage1_time_str", "stage2_time_str"]:
                df[col] = ""
                df[col] = df[col].astype("string")
            elif col in ["stage1_time", "stage2_time"]:
                df[col] = 0.0
                df[col] = df[col].astype(float)
            else:
                df[col] = None
                df[col] = df[col].astype("object")
    return df


# === Main entry point ===


def main():
    """
    Main entry point for the pipeline.
    - Stage 1 (parallel): generate reports & READMEs for all repositories.
    - Stage 2 (sequential): generate docstrings for repositories not yet processed.
    """

    # Create a command line argument parser
    parser = build_parser_from_yaml(extra_sections=["settings", "arguments", "multi-run"])
    args = parser.parse_args()

    # Load table containing repository URLs
    df = load_table(args.table_path)
    repositories = df["repository"].dropna().tolist()

    # Load prompts
    prompts = PromptLoader()

    # Stage 1: Parallel run for unprocessed repos
    unprocessed_stage1 = [r for r in repositories if not df.loc[df["repository"] == r, "processed_stage1"].any()]

    if unprocessed_stage1:
        rich_section(f"Starting Stage 1 for {len(unprocessed_stage1)} repositories (parallel mode)")
        with ProcessPoolExecutor(max_workers=os.cpu_count() // 2 or 2) as executor:
            futures = {
                executor.submit(process_repository_stage1, repo, prompts, args): repo for repo in unprocessed_stage1
            }
            for future in as_completed(futures):
                repo = futures[future]
                try:
                    result = future.result()
                    for key, value in result.items():
                        if key in df.columns:
                            df.loc[df["repository"] == repo, key] = value

                    # Save progress incrementally
                    try:
                        if args.table_path.endswith(".csv"):
                            df.to_csv(args.table_path, index=False)
                        else:
                            df.to_excel(args.table_path, index=False)
                    except PermissionError:
                        logger.warning(
                            f"Cannot save table '{args.table_path}'. "
                            "If you know you have access to this file, "
                            "try to close applications that are using it."
                        )

                except Exception as e:
                    logger.error(f"Stage 1 failed for {repo} — {e}")

    else:
        rich_section("All repositories already processed in Stage 1")

    # Stage 2: Sequential docstring generation
    if args.docstring:
        unprocessed_stage2 = [r for r in repositories if not df.loc[df["repository"] == r, "processed_docstring"].any()]
        if unprocessed_stage2:
            rich_section(f"Starting Stage 2 (docstrings) for {len(unprocessed_stage2)} repositories (sequential mode)")
            for repo_url in unprocessed_stage2:
                process_docstrings_for_repo(repo_url, args, df)
        else:
            rich_section("All repositories already processed for docstrings")
    else:
        rich_section("Skipping Stage 2 — docstring generation disabled")

    rich_section("Pipeline completed successfully.")


if __name__ == "__main__":
    main()
