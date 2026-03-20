import asyncio
import logging
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd
from pandas import DataFrame

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitHubAgent, GitLabAgent, GitverseAgent
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.analysis.repository_report.report_maker import ReportGenerator
from osa_tool.operations.codebase.docstring_generation.docstring_generation import DocstringsGenerator
from osa_tool.operations.docs.readme_generation.context.pypi_status_checker import PyPiPackageInspector
from osa_tool.operations.docs.readme_generation.readme_core import ReadmeAgent
from osa_tool.operations.docs.readme_generation.utils import format_time
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.arguments_parser import build_parser_from_yaml
from osa_tool.utils.utils import logger, rich_section, parse_git_url, delete_repository

# === Stage 1: Generate report and README asynchronously ===


async def generate_report(config_manager: ConfigManager, metadata: RepositoryMetadata, args) -> None:
    """
    Asynchronously generates a PDF report for a repository and saves it to a reports directory.
    
    This function serves as an async wrapper around the synchronous PDF generation process,
    allowing it to be run in an asynchronous context without blocking. It creates a 'reports'
    directory adjacent to the provided table path, then builds and saves the PDF report.
    
    Args:
        config_manager: Manages configuration settings used during report generation.
        metadata: Contains repository metadata (e.g., name) used to title the report.
        args: Contains the table_path used to determine the output directory for the report.
    
    Why:
        The method uses asyncio.to_thread to offload the CPU‑intensive PDF building to a
        separate thread, preventing it from blocking the async event loop while maintaining
        compatibility with synchronous report‑generation code.
    """
    reports_dir = os.path.join(os.path.dirname(args.table_path), "reports")
    os.makedirs(reports_dir, exist_ok=True)

    report_gen = ReportGenerator(config_manager, metadata)
    report_gen.output_path = os.path.join(reports_dir, f"{metadata.name}_report.pdf")

    await asyncio.to_thread(report_gen.build_pdf)


async def generate_readme(config_manager: ConfigManager, metadata: RepositoryMetadata, args) -> None:
    """
    Asynchronously generates a README file for a repository and saves it to a designated directory.
    
    This function serves as an asynchronous wrapper around the synchronous README generation logic. It ensures the output directory exists, configures the ReadmeAgent with the necessary parameters, and then executes the generation in a separate thread to avoid blocking the event loop.
    
    Args:
        config_manager: The configuration manager instance providing settings and environment.
        metadata: The repository metadata containing details like the repository name.
        args: An object containing command-line or runtime arguments, specifically expecting `table_path` to determine the output directory and `refine_readme` to control README refinement.
    
    Why:
        The asynchronous design allows the potentially I/O-bound or CPU-intensive README generation to run without blocking other concurrent operations, improving overall tool responsiveness when processing multiple repositories or tasks.
    """
    readmes_dir = os.path.join(os.path.dirname(args.table_path), "readmes")
    os.makedirs(readmes_dir, exist_ok=True)

    readme_agent = ReadmeAgent(config_manager, metadata, None, args.refine_readme)
    readme_agent.file_to_save = os.path.join(readmes_dir, f"{metadata.name}_README.md")

    await asyncio.to_thread(readme_agent.generate_readme)


async def run_async_tasks(config_manager: ConfigManager, git_agent, args):
    """
    Run report and readme generation concurrently inside a process.
    
    Based on command-line arguments, creates and executes asynchronous tasks for
    generating a PDF report and/or a README file. Tasks are run concurrently using
    `asyncio.gather`.
    
    Args:
        config_manager: Manages configuration settings for the generation tasks.
        git_agent: Provides repository metadata used by the generation tasks.
        args: Command-line arguments specifying which tasks to run (`args.report`
              and/or `args.readme`) and providing additional options.
    
    Why:
        This method allows the potentially independent report and readme generation
        operations to execute in parallel, improving overall performance when both
        are requested.
    """
    tasks = []

    if args.report:
        tasks.append(asyncio.create_task(generate_report(config_manager, git_agent.metadata, args)))
    if args.readme:
        tasks.append(asyncio.create_task(generate_readme(config_manager, git_agent.metadata, args)))
    if tasks:
        await asyncio.gather(*tasks)


def process_repository_stage1(repo_url: str, args) -> dict:
    """
    Stage 1: Clone repository, generate report and README asynchronously.
    This stage runs in multiple processes concurrently.
    
    It clones the given repository, runs concurrent tasks to generate a PDF report
    and/or a README file (as specified by command‑line arguments), collects
    package metadata from PyPI, and records timing and success status.
    
    Args:
        repo_url: The URL of the Git repository to process.
        args: Command‑line arguments object containing configuration such as
              `table_path`, `docstring`, `report`, and `readme` flags.
    
    Returns:
        A dictionary with the following keys:
            - repository: The input repository URL.
            - name: The repository name extracted from the URL.
            - forks: The fork count from the repository metadata.
            - stars: The star count from the repository metadata.
            - downloads: The download count from PyPI, if available.
            - processed_stage1: Boolean indicating whether stage 1 completed successfully.
            - processed_docstring: Boolean (always False at this stage; reserved for later use).
            - stage1_time: Total processing time in seconds.
            - stage1_time_str: Human‑readable formatted processing time (HH:MM:SS).
    
    Why:
        This stage is designed to be executed in parallel across multiple repositories.
        It performs the initial heavy‑weight operations—cloning and generating
        documentation—while gathering metadata needed for later analysis. The
        repository is automatically cleaned up after stage 1 unless docstring
        generation is requested in a later stage.
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
        config_manager = ConfigManager(args)

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
        sourcerank = SourceRank(config_manager)

        # Run async stage (report + readme)
        asyncio.run(run_async_tasks(config_manager, git_agent, args))

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
    
    This method handles the docstring generation for a single repository. It sets up the necessary working directories and logging, runs the docstring generator, records the processing time, and updates the progress table. The table is saved after each repository to prevent data loss in case of interruptions.
    
    Args:
        repo_url: The URL of the Git repository to process.
        args: An object containing configuration arguments, including the table file path and an ignore list.
        df: The DataFrame representing the progress table, which will be updated with the results.
    
    Why:
        The table is updated and saved immediately after each repository to ensure progress is persisted, minimizing data loss if the process fails or is stopped. Logging is configured per repository to isolate and capture output specific to each run.
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
        config_manager = ConfigManager(args)

        # Generate docstrings
        DocstringsGenerator(config_manager, args.ignore_list).run()

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
    """
    Load a repository table from a CSV or Excel file, performing validation and adding missing columns with default values.
    
    The method ensures the input file exists, is in a supported format, and contains a required 'repository' column. It then loads the data and initializes optional columns that are expected by downstream processing stages. If any validation fails, the program exits with an error.
    
    Args:
        table_path: Path to the CSV or Excel file containing the repository data. Must be provided and point to an existing file with a .csv or .xlsx extension.
    
    Returns:
        A pandas DataFrame containing the repository table. The DataFrame is guaranteed to have a 'repository' column and will include the following columns with default values if they were missing from the input file:
            - name, stage1_time_str, stage2_time_str: Empty strings.
            - forks, stars, downloads: None values.
            - processed_stage1, processed_docstring: False.
            - stage1_time, stage2_time: 0.0.
        This ensures the DataFrame has a consistent structure for subsequent pipeline stages.
    """
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
    
    The pipeline processes a list of repositories in two stages:
    - Stage 1 (parallel): Generates reports and READMEs for all repositories that have not yet been processed in this stage. This stage runs in parallel using multiple worker processes.
    - Stage 2 (sequential): Generates docstrings for repositories that have not yet been processed in this stage, but only if the `--docstring` command-line flag is enabled. This stage runs sequentially.
    
    Progress is tracked and saved incrementally in a table (CSV or Excel file). The table must contain a 'repository' column and is automatically updated with results and status flags after each repository is processed.
    
    Args:
        No explicit parameters. Command-line arguments are parsed internally. Key arguments include:
            --table-path: Path to the input table file containing repository URLs.
            --docstring: Flag to enable or disable Stage 2 docstring generation.
    
    Why:
        Stage 1 is parallelized to speed up the generation of reports and READMEs across many repositories.
        Stage 2 is sequential because docstring generation may involve more intensive processing or shared resources where parallel execution could cause conflicts.
        Incremental saving ensures progress is not lost if the pipeline is interrupted, though a PermissionError warning is logged if the file cannot be written.
    """

    # Create a command line argument parser
    parser = build_parser_from_yaml(extra_sections=["settings", "arguments", "multi-run"])
    args = parser.parse_args()

    # Load table containing repository URLs
    df = load_table(args.table_path)
    repositories = df["repository"].dropna().tolist()

    # Stage 1: Parallel run for unprocessed repos
    unprocessed_stage1 = [r for r in repositories if not df.loc[df["repository"] == r, "processed_stage1"].any()]

    if unprocessed_stage1:
        rich_section(f"Starting Stage 1 for {len(unprocessed_stage1)} repositories (parallel mode)")
        with ProcessPoolExecutor(max_workers=os.cpu_count() // 2 or 2) as executor:
            futures = {executor.submit(process_repository_stage1, repo, args): repo for repo in unprocessed_stage1}
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
