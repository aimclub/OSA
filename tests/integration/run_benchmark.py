import asyncio
import json
import logging
import os
import shutil
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from typing import Any, Optional, Type

import pandas as pd
import requests
from pandas import DataFrame
from pydantic import BaseModel

from deepeval.metrics import GEval
from deepeval.models.base_model import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCase, LLMTestCaseParams

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitHubAgent, GitLabAgent, GitverseAgent
from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.operations.docs.readme_generation.readme_agent import ReadmeAgent
from osa_tool.tools.repository_analysis.sourcerank import SourceRank
from osa_tool.utils.arguments_parser import build_parser_from_yaml
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import delete_repository, format_time, parse_git_url, rich_section

README_QUALITY_CRITERIA = """
Determine whether the AI-generated Readme file (ACTUAL_OUTPUT)
is better than the original one (EXPECTED_OUTPUT).
ACTUAL_OUTPUT contains two fields: 'readme', which contains the generated README itself,
and 'repo_structure' which is json with repository's structure.
Generated README's content must be consistent with the provided repository structure.
The ACTUAL_OUTPUT does not necessary have to be the same as EXPECTED_OUTPUT,
Your goal is to determine which text is better, using the provided Evaluations steps.
Readme structure does not matter much as long as it passes the evaluation steps.
"""

README_QUALITY_STEPS = [
    "Step 1: Does the provided structure of the repository address README content?",
    "Step 2: Does the README provide a clear and accurate overview of the repository's purpose?",
    "Step 3: Are installation and setup instructions included and easy to follow?",
    "Step 4: Are usage examples provided and do they clearly demonstrate functionality?",
    "Step 5: Are dependencies or requirements listed appropriately?",
    "Step 6: Is the README easy to read, well-structured, and free of confusing language?",
]


def _strip_markdown_json_fence(text: str) -> str:
    cleaned = text.strip()
    if not cleaned.startswith("```"):
        return cleaned
    cleaned = cleaned.removeprefix("```").strip()
    if cleaned.lower().startswith("json"):
        cleaned = cleaned[4:].lstrip()
    if "```" in cleaned:
        cleaned = cleaned.split("```", 1)[0].strip()
    return cleaned


class CustomLLM(DeepEvalBaseLLM):
    def __init__(
        self,
        api: str = "openrouter",
        model: str = "gpt-4.1",
        url: str = "https://openrouter.ai/api/v1",
        *,
        max_tokens: int = 1024,
        request_timeout: float = 180.0,
        use_json_object_mode: bool = True,
    ):
        self.api = api
        self.model_name = model
        self.url = url.rstrip("/")
        self.max_tokens = max_tokens
        self.request_timeout = request_timeout
        self.use_json_object_mode = use_json_object_mode

    def load_model(self):
        return self

    def supports_json_mode(self) -> bool:
        return True

    def get_model_name(self) -> str:
        return self.model_name

    def _api_key(self) -> str:
        api = (self.api or "").lower().strip()
        url = (self.url or "").lower()
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        openai_key = os.getenv("OPENAI_API_KEY", "")
        service_key = os.getenv("LLM_SERVICE_KEY", "")
        if api == "openrouter" or "openrouter.ai" in url:
            return openrouter_key or openai_key or service_key
        if api == "openai":
            return openai_key or openrouter_key or service_key
        return openrouter_key or openai_key or service_key

    def _headers(self) -> dict[str, str]:
        key = self._api_key()
        if not key:
            return {}
        headers = {
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        }
        if "openrouter.ai" in self.url.lower():
            headers["HTTP-Referer"] = "https://github.com/aimclub/OSA"
            headers["X-Title"] = "OSA README benchmark"
        return headers

    def _post_chat(self, messages: list[dict[str, str]], *, response_format: Optional[dict[str, str]] = None) -> str:
        headers = self._headers()
        if not headers:
            raise RuntimeError("Missing judge API key. Set OPENROUTER_API_KEY, OPENAI_API_KEY, or LLM_SERVICE_KEY.")
        payload: dict[str, Any] = {
            "model": self.model_name,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "temperature": 0.0,
        }
        if response_format and self.use_json_object_mode:
            payload["response_format"] = response_format

        response = requests.post(
            f"{self.url}/chat/completions", headers=headers, json=payload, timeout=self.request_timeout
        )
        if response.status_code == 200:
            return (response.json()["choices"][0]["message"]["content"] or "").strip()

        if response_format and self.use_json_object_mode:
            payload.pop("response_format", None)
            response = requests.post(
                f"{self.url}/chat/completions", headers=headers, json=payload, timeout=self.request_timeout
            )
            if response.status_code == 200:
                return (response.json()["choices"][0]["message"]["content"] or "").strip()

        raise RuntimeError(f"Judge LLM HTTP {response.status_code}: {response.text[:500]}")

    def generate(self, prompt: str) -> str:
        return self._post_chat([{"role": "user", "content": prompt}])

    async def a_generate(self, prompt: str, schema=None):
        return await asyncio.to_thread(self.generate, prompt)


def generate_readme(config_manager: ConfigManager, metadata: RepositoryMetadata, args, safe_name: str) -> str:
    readmes_dir = os.path.join(os.path.dirname(args.table_path), "readmes")
    os.makedirs(readmes_dir, exist_ok=True)

    readme_agent = ReadmeAgent(config_manager=config_manager, metadata=metadata)
    dest_path = os.path.join(readmes_dir, f"{safe_name}_README.md")
    readme_agent.file_to_save = dest_path

    readme_agent.generate_readme()

    src = os.path.join(readme_agent.repo_path, "README.md")
    if os.path.isfile(src):
        shutil.copy2(src, dest_path)
    else:
        logger.warning(f"README not found at clone path after generation: {src}")

    return dest_path


def get_repo_structure_json(repo_path: str) -> str:
    """Gathers a simple repository structure for GEVAL."""
    tree = []
    for root, dirs, files in os.walk(repo_path):
        if ".git" in dirs:
            dirs.remove(".git")
        rel_path = os.path.relpath(root, repo_path)
        tree.append({"dir": rel_path if rel_path != "." else "/", "files": files})
    return json.dumps(tree, ensure_ascii=False)


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

    result = {"repository": repo_url, "name": repo_name, "status": "Failed", "geval_score": None}

    try:
        args.repository = repo_url
        config_manager = ConfigManager(args)

        if not hasattr(config_manager.config, "git"):
            config_manager.config.git = type("obj", (object,), {"repository": repo_url})
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

        actual_clone_path = os.path.join(worker_dir, repo_name)

        expected_output = ""
        original_readme_path = os.path.join(actual_clone_path, "README.md")

        if not os.path.exists(original_readme_path):
            original_readme_path = os.path.join(actual_clone_path, "readme.md")

        if os.path.exists(original_readme_path):
            with open(original_readme_path, "r", encoding="utf-8", errors="replace") as f:
                expected_output = f.read()

        repo_structure = get_repo_structure_json(actual_clone_path)

        SourceRank(config_manager)
        dest_path = generate_readme(config_manager, git_agent.metadata, args, safe_name)

        if os.path.exists(dest_path):
            result.update({"name": git_agent.metadata.name, "status": "Success"})
            logger.info(f"Successfully generated README in {format_time(time.time() - stage_start)}")

            logger.info("Starting GEVAL assessment...")
            with open(dest_path, "r", encoding="utf-8", errors="replace") as f:
                generated_readme = f.read()

            judge_model = CustomLLM(api=args.api, model=args.model, url=args.base_url)
            metric = GEval(
                name="Readme quality",
                criteria=README_QUALITY_CRITERIA,
                evaluation_steps=README_QUALITY_STEPS,
                evaluation_params=[LLMTestCaseParams.ACTUAL_OUTPUT, LLMTestCaseParams.EXPECTED_OUTPUT],
                model=judge_model,
                verbose_mode=False,
                async_mode=False,
            )

            test_case = LLMTestCase(
                input="",
                actual_output=json.dumps(
                    {"readme": generated_readme, "repo_structure": repo_structure}, ensure_ascii=False
                ),
                expected_output=expected_output,
            )

            try:
                metric.measure(test_case)
                result["geval_score"] = metric.score
                logger.info(f"GEVAL Score: {metric.score}")
            except Exception as e:
                logger.error(f"GEval metric measurement failed: {e}")

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
    if not os.path.isfile(table_path):
        test_repos = [
            "https://github.com/google/python-fire",
            "https://github.com/encode/httpx",
            "https://github.com/AntonOsika/gpt-engineer",
            "https://github.com/THUDM/ChatGLM-6B",
        ]

        rows = [{"repository": repo, "status": "Pending", "geval_score": None} for repo in test_repos]
        df = pd.DataFrame(rows)
        df.to_csv(table_path, index=False)
        logger.info(f"Created new benchmark run at {table_path} with {len(test_repos)} repos.")
        return df

    df = pd.read_csv(table_path) if table_path.endswith(".csv") else pd.read_excel(table_path)

    if "repository" not in df.columns:
        if "repo_url" in df.columns:
            df["repository"] = df["repo_url"]
        else:
            logger.error("Table must contain a 'repository' or 'repo_url' column.")
            sys.exit(1)

    if "status" not in df.columns:
        df["status"] = "Pending"
    if "geval_score" not in df.columns:
        df["geval_score"] = None

    return df


def main():
    parser = build_parser_from_yaml(extra_sections=["settings", "arguments", "multi-run"])
    args, _ = parser.parse_known_args()

    if getattr(args, "table_path", None) is None:
        results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "benchmark_results"))
        os.makedirs(results_dir, exist_ok=True)
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        args.table_path = os.path.join(results_dir, f"run_{timestamp}.csv")

    if getattr(args, "api", None) is None:
        args.api = "openai"
    if getattr(args, "base_url", None) is None:
        args.base_url = "https://openrouter.ai/api/v1"
    if getattr(args, "model", None) is None:
        args.model = "openai/gpt-4.1"

    args.table_path = os.path.abspath(args.table_path)

    df = load_table(args.table_path)
    repos = df["repository"].dropna().tolist()

    unprocessed = [r for r in repos if df.loc[df["repository"] == r, "status"].values[0] != "Success"]

    if unprocessed:
        rich_section(f"Starting lightweight README Generation & GEVAL for {len(unprocessed)} repos")
        with ProcessPoolExecutor(max_workers=max(1, os.cpu_count() // 2)) as executor:
            futures = {executor.submit(process_repository, repo, args): repo for repo in unprocessed}
            for future in as_completed(futures):
                repo = futures[future]
                try:
                    res = future.result()
                    df.loc[df["repository"] == repo, "status"] = res["status"]
                    df.loc[df["repository"] == repo, "geval_score"] = res.get("geval_score")

                    if args.table_path.endswith(".csv"):
                        df.to_csv(args.table_path, index=False)
                    else:
                        df.to_excel(args.table_path, index=False)
                except Exception as e:
                    logger.error(f"Failed to process {repo} — {e}")

        print("\n" + "=" * 90)
        print(" FINAL BENCHMARK RESULTS ".center(90, "="))
        print("=" * 90)
        print(df.to_string(index=False))
        print("=" * 90)
        print(f"All files (logs, readmes, table) saved to: {os.path.dirname(args.table_path)}\n")
    else:
        rich_section("All repositories processed successfully.")


if __name__ == "__main__":
    main()
