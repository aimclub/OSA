import logging
import os
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

import pandas as pd
from pandas import DataFrame

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitHubAgent, GitLabAgent, GitverseAgent
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.docs.readme_generation.readme_agent import ReadmeAgent
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.arguments_parser import build_parser_from_yaml
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import delete_repository, format_time, parse_git_url, rich_section


def generate_readme(config_manager: ConfigManager, metadata: RepositoryMetadata, args, safe_name: str) -> str:
    readmes_dir = os.path.join(os.path.dirname(args.table_path), "readmes")
    os.makedirs(readmes_dir, exist_ok=True)

    readme_agent = ReadmeAgent(
        config_manager=config_manager,
        metadata=metadata,
    )

    dest_path = os.path.join(readmes_dir, f"{safe_name}_README.md")
    readme_agent.file_to_save = dest_path

    readme_agent.generate_readme()

    src = os.path.join(readme_agent.repo_path, "README.md")
    if os.path.isfile(src):
        shutil.copy2(src, dest_path)
    else:
        logger.warning(f"README not found at clone path after generation: {src}")
        
    return dest_path


def process_repository(repo_url: str, args) -> dict:
    stage_start = time.time()

    repos_dir = os.path.join(os.path.dirname(args.table_path), "repositories")
    logs_dir = os.path.join(os.path.dirname(args.table_path), "logs")
    os.makedirs(logs_dir, exist_ok=True)
    os.makedirs(repos_dir, exist_ok=True)

    _, _, repo_name, _ = parse_git_url(repo_url)
    
    url_parts = repo_url.rstrip("/").split("/")
    safe_name = f"{url_parts[-2]}_{url_parts[-1]}" if len(url_parts) >= 2 else repo_name

    worker_dir = os.path.join(repos_dir, safe_name)
    os.makedirs(worker_dir, exist_ok=True)

    original_cwd = os.getcwd()
    os.chdir(worker_dir)

    log_file = os.path.join(logs_dir, f"{safe_name}.log")

    logger.setLevel(logging.DEBUG)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(file_handler)

    result = {"repository": repo_url, "name": repo_name, "status": "Failed"}

    try:
        args.repository = repo_url
        config_manager = ConfigManager(args)

        if not hasattr(config_manager.config, 'git'):
            config_manager.config.git = type('obj', (object,), {'repository': repo_url})
        else:
            config_manager.config.git.repository = repo_url

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
        SourceRank(config_manager)
        dest_path = generate_readme(config_manager, git_agent.metadata, args, safe_name)

        if os.path.exists(dest_path):
            result.update({"name": git_agent.metadata.name, "status": "Success"})
            logger.info(f"Successfully generated README in {format_time(time.time() - stage_start)}")
        else:
            result.update({"name": git_agent.metadata.name, "status": "Failed"})
            logger.error(f"Failed to generate README for {git_agent.metadata.name}")

    except Exception as e:
        logger.error(f"Error processing {repo_url}: {e}")

    finally:
        file_handler.flush()
        file_handler.close()
        logger.removeHandler(file_handler)
        delete_repository(repo_url)
        os.chdir(original_cwd)
        shutil.rmtree(worker_dir, ignore_errors=True)

    return result


def load_table(table_path: str) -> DataFrame:
    if not table_path or not os.path.isfile(table_path):
        logger.error(f"Table file missing or invalid: {table_path}")
        sys.exit(1)

    df = pd.read_csv(table_path) if table_path.endswith(".csv") else pd.read_excel(table_path)

    if "repository" not in df.columns:
        if "repo_url" in df.columns:
            df["repository"] = df["repo_url"]
        else:
            logger.error("Table must contain a 'repository' or 'repo_url' column.")
            sys.exit(1)

    if "status" not in df.columns:
        df["status"] = "Pending"
    return df


def main():
    parser = build_parser_from_yaml(extra_sections=["settings", "arguments", "multi-run"])
    args, _ = parser.parse_known_args()

    if getattr(args, "table_path", None) is None:
        raise ValueError("Missing required argument: --table-path")

    args.table_path = os.path.abspath(args.table_path)

    df = load_table(args.table_path)
    repos = df["repository"].dropna().tolist()

    unprocessed = [r for r in repos if df.loc[df["repository"] == r, "status"].values[0] != "Success"]

    if unprocessed:
        rich_section(f"Starting lightweight README Generation for {len(unprocessed)} repos")
        with ProcessPoolExecutor(max_workers=max(1, os.cpu_count() // 2)) as executor:
            futures = {executor.submit(process_repository, repo, args): repo for repo in unprocessed}
            for future in as_completed(futures):
                repo = futures[future]
                try:
                    df.loc[df["repository"] == repo, "status"] = future.result()["status"]
                    if args.table_path.endswith(".csv"):
                        df.to_csv(args.table_path, index=False)
                    else:
                        df.to_excel(args.table_path, index=False)
                except Exception as e:
                    logger.error(f"Failed to process {repo} — {e}")
    else:
        rich_section("All repositories processed successfully.")


if __name__ == "__main__":
    main()
