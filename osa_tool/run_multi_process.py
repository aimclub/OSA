import asyncio
import os
import sys
import time

import pandas as pd
from pandas import DataFrame

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.analytics.report_maker import ReportGenerator
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.arguments_parser import build_parser_from_yaml
from osa_tool.config.settings import ConfigLoader
from osa_tool.git_agent.git_agent import GitHubAgent, GitLabAgent, GitverseAgent
from osa_tool.readmegen.context.pypi_status_checker import PyPiPackageInspector
from osa_tool.readmegen.readme_core import ReadmeAgent
from osa_tool.readmegen.utils import format_time
from osa_tool.run import load_configuration
from osa_tool.utils import logger, rich_section, delete_repository


async def generate_report(
    config: ConfigLoader, sourcerank: SourceRank, metadata: RepositoryMetadata, table_path: str
) -> None:
    reports_dir = os.path.join(os.path.dirname(table_path), "reports")
    os.makedirs(reports_dir, exist_ok=True)
    analytics = ReportGenerator(config, sourcerank, metadata)
    analytics.output_path = os.path.join(reports_dir, f"{metadata.name}_report.pdf")
    analytics.build_pdf()


async def generate_readme(
    config: ConfigLoader,
    metadata: RepositoryMetadata,
    refine_readme: bool,
    table_path: str,
) -> None:
    readmes_dir = os.path.join(os.path.dirname(table_path), "readmes")
    os.makedirs(readmes_dir, exist_ok=True)
    readme_agent = ReadmeAgent(config, None, refine_readme, metadata)
    readme_agent.file_to_save = os.path.join(readmes_dir, f"{metadata.name}_README.md")
    await asyncio.to_thread(readme_agent.generate_readme)


async def process_repository_async(repo_url: str, args) -> dict:
    start_time = time.time()
    result = {
        "repository": repo_url,
        "name": None,
        "elapsed_time": None,
        "forks": None,
        "stars": None,
        "downloads": None,
        "processed": False,
    }

    try:
        # Load configuration
        config = await asyncio.to_thread(
            load_configuration,
            repo_url,
            args.api,
            args.base_url,
            args.model,
            args.temperature,
            args.max_tokens,
            args.top_p,
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
            return result

        await asyncio.to_thread(git_agent.clone_repository)

        sourcerank = SourceRank(config)

        tasks = []
        if args.report:
            tasks.append(generate_report(config, sourcerank, git_agent.metadata, args.table_path))
        if args.readme:
            tasks.append(generate_readme(config, git_agent.metadata, args.refine_readme, args.table_path))
        if tasks:
            await asyncio.gather(*tasks)

        # Get downloads from pepy.tech if exists
        info = await asyncio.to_thread(PyPiPackageInspector(sourcerank.tree, sourcerank.repo_path).get_info)
        downloads_count = info.get("downloads") if info else ""

        # Update result
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
        logger.error(f"Error processing {repo_url}: {e}")

    finally:
        elapsed = time.time() - start_time
        result["elapsed_time"] = format_time(elapsed)
        rich_section(f"Repository {repo_url} processed in {result['elapsed_time']}")
        await asyncio.to_thread(delete_repository, repo_url)

    return result


async def main_async(repositories, args, df, max_workers: int = 4):
    sem = asyncio.Semaphore(max_workers)

    async def sem_task(repo):
        async with sem:
            return await process_repository_async(repo, args)

    overall_start = time.time()
    results = await asyncio.gather(*(sem_task(repo) for repo in repositories))
    total_elapsed = format_time(time.time() - overall_start)

    for res in results:
        repo = res["repository"]
        for key, value in res.items():
            if key in df.columns:
                df.loc[df["repository"] == repo, key] = value

    # Save table
    if args.table_path.endswith(".csv"):
        df.to_csv(args.table_path, index=False)
    else:
        df.to_excel(args.table_path, index=False)

    rich_section(f"All repositories processed in total time: {total_elapsed}")


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


def main():
    parser = build_parser_from_yaml(extra_sections=["multi-run"])
    args = parser.parse_args()
    df = load_table(args.table_path)

    repositories = df["repository"].dropna().tolist()
    unprocessed = [r for r in repositories if not df.loc[df["repository"] == r, "processed"].any()]
    if not unprocessed:
        rich_section("All repositories already processed.")
        sys.exit(0)

    asyncio.run(main_async(unprocessed, args, df, max_workers=os.cpu_count() // 2))


if __name__ == "__main__":
    main()
