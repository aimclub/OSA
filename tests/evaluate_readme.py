import argparse
import os
import subprocess
from typing import Dict, Any

import pandas as pd

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.docs.readme_generation.pipeline.nodes.self_eval import self_eval_node
from osa_tool.operations.docs.readme_generation.pipeline.runtime_context import ReadmeContext
from osa_tool.operations.docs.readme_generation.pipeline.state import ReadmeState
from osa_tool.operations.docs.readme_generation.readme_agent import ReadmeAgent

REPOS_SMALL = [
    "https://github.com/google/python-fire",
    "https://github.com/encode/httpx",
    "https://github.com/AntonOsika/gpt-engineer",
    "https://github.com/THUDM/ChatGLM-6B"
]


def get_minimal_metadata(repo_url: str) -> RepositoryMetadata:
    parts = repo_url.rstrip('/').split('/')
    owner = parts[-2] if len(parts) >= 2 else "unknown"
    name = parts[-1] if len(parts) >= 1 else "unknown"

    return RepositoryMetadata(
        name=name,
        full_name=f"{owner}/{name}",
        owner=owner,
        owner_url=f"https://github.com/{owner}",
        description="",
        stars_count=0,
        forks_count=0,
        watchers_count=0,
        open_issues_count=0,
        default_branch="main",
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
        pushed_at="2024-01-01T00:00:00Z",
        size_kb=1000,
        clone_url_http=f"{repo_url}.git",
        clone_url_ssh=f"git@github.com:{owner}/{name}.git",
        contributors_url=f"https://github.com/{owner}/{name}/contributors",
        languages_url=f"https://api.github.com/repos/{owner}/{name}/languages",
        issues_url=f"https://api.github.com/repos/{owner}/{name}/issues",
        language="Unknown",
        languages={},
        topics=[],
        has_wiki=False,
        has_issues=False,
        has_projects=False,
        is_private=False,
        homepage_url="",
        license_name="MIT",
        license_url=""
    )


def load_all_repos(csv_path: str = "repo_list.csv") -> list[str]:
    if not os.path.exists(csv_path):
        print(f"[!] File {csv_path} not found.")
        return []
    df = pd.read_csv(csv_path)
    return df['repo_url'].tolist()


def evaluate_final_readme(
    repo_url: str,
    readme_content: str,
    config: ConfigManager,
    metadata: RepositoryMetadata
) -> Dict[str, Any]:
    ctx = ReadmeContext(config, metadata)
    state = ReadmeState(
        repo_url=repo_url,
        readme_draft=readme_content,
        refinement_cycles=0,
        section_plan=[]
    )
    eval_result = self_eval_node(state, ctx)
    return {
        "score": eval_result.get("refinement_score", 0.0),
        "issues": eval_result.get("refinement_issues", []),
        "structured_issues": eval_result.get("refinement_structured_issues", [])
    }


def main():
    parser = argparse.ArgumentParser(description="README Generation Benchmark")
    parser.add_argument(
        "--mode",
        choices=["small", "full"],
        default="small",
        help="small: 4 test repos | full: all repos from csv"
    )
    args = parser.parse_args()

    repos = REPOS_SMALL if args.mode == "small" else load_all_repos()
    if not repos:
        return

    print(f"\n[>>>] Starting benchmark (Mode: {args.mode}). Total repositories: {len(repos)}\n")

    benchmark_results = []

    for repo_url in repos:
        print(f"\n[{repo_url}] Preparing")

        repo_name = repo_url.rstrip('/').split('/')[-1]
        target_dir = os.path.join(os.getcwd(), repo_name)

        if not os.path.exists(target_dir) or not os.listdir(target_dir):
            print(f"[{repo_url}] Cloning repository")
            try:
                subprocess.run(
                    ["git", "clone", "--depth", "1", repo_url, target_dir],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except subprocess.CalledProcessError:
                print(f"[{repo_url}] Git clone failed")
                benchmark_results.append({"repo": repo_url, "score": 0.0, "status": "Clone failed"})
                continue
        else:
            print(f"[{repo_url}] Repository already exists")

        print(f"[{repo_url}] Starting generation")

        config = ConfigManager()
        original_get = config.get_model_settings

        def forced_get_model_settings(op_name):
            settings = original_get(op_name)
            target_model = "gpt-4o-mini"
            try:
                settings.model = target_model
            except AttributeError:
                try:
                    settings["model"] = target_model
                except (TypeError, KeyError):
                    pass
            except Exception:
                pass
            return settings

        config.get_model_settings = forced_get_model_settings

        metadata = get_minimal_metadata(repo_url)

        try:
            agent = ReadmeAgent(
                config_manager=config,
                metadata=metadata
            )
            agent.repo_url = repo_url
            agent.generate_readme()

            readme_path = os.path.join(target_dir, "README.md")

        except Exception as e:
            print(f"[{repo_url}] Agent crashed during execution: {e}\n")
            benchmark_results.append({"repo": repo_url, "score": 0.0, "status": "Failed to generate"})
            continue

        if not readme_path or not os.path.exists(readme_path):
            print(f"[{repo_url}] Generation failed (file not found)\n")
            benchmark_results.append({"repo": repo_url, "score": 0.0, "status": "Failed to generate"})
            continue

        with open(readme_path, "r", encoding="utf-8") as f:
            readme_content = f.read()

        print(f"[{repo_url}] Evaluating generated README (Length: {len(readme_content)} chars)...")
        eval_metrics = evaluate_final_readme(repo_url, readme_content, config, metadata)
        score = eval_metrics["score"]
        issues_count = len(eval_metrics["issues"])

        print(f"[{repo_url}] Score: {score}/10.0 | Issues found: {issues_count}\n")

        benchmark_results.append({
            "repo": repo_url,
            "score": score,
            "issues_count": issues_count,
            "status": "Success",
            "issues_preview": eval_metrics["issues"]
        })

    print("BENCHMARK RESULTS")

    total_score = 0
    success_count = 0

    for res in benchmark_results:
        print(f"Repo: {res['repo']}")
        print(f"Status: {res['status']}")
        if res['status'] == "Success":
            print(f"Score: {res['score']}/10.0")
            print(f"Issues: {res['issues_count']}")
            if res['issues_preview']:
                print("Top 3 issues:")
                for i in res['issues_preview'][:3]:
                    print(f"  - {i}")
        print("-" * 30)

        if res['status'] == "Success":
            total_score += res['score']
            success_count += 1

    if success_count > 0:
        avg_score = total_score / success_count
        print(f"\nAverage Generation Score: {avg_score:.2f} / 10.0")


if __name__ == "__main__":
    main()