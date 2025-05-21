import json
import logging
import os
import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Optional

import pandas as pd
import requests
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, LLMTestCaseParams
from dotenv import load_dotenv
from rich.logging import RichHandler

from osa_tool.github_agent.github_agent import GithubAgent
from osa_tool.models.models import ModelHandlerFactory
from osa_tool.readmeai.config.settings import ConfigLoader, GitSettings
from osa_tool.readmeai.deepeval_checker import CustomLLM
from osa_tool.readmeai.readme_core import readme_agent
from osa_tool.readmeai.readmegen_article.config.settings import ArticleConfigLoader
from osa_tool.utils import osa_project_root
from struct_to_json import build_tree, tree_to_dict

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()],
)

logger = logging.getLogger("rich")


def parse_github_url(repo_url: str):
    pattern = r"https://github\.com/([^/]+)/([^/]+)/tree/([a-f0-9]+)"
    match = re.match(pattern, repo_url)
    if match:
        return match
    else:
        logger.error(f"URL {repo_url} does not match expected format.")



def load_configuration(
    repo_url: str, api: str, model_name: str, url: str, article: Optional[str]
) -> ConfigLoader:
    """
    Loads configuration for osa_tool.

    Args:
        repo_url (str): URL of the GitHub repository.
        api (str): LLM API service provider.
        model_name (str): Specific LLM model to use.
        article (Optional[str]): Link to the pdf file of the article. Can be None.

    Returns:
        config_loader: The configuration object which contains settings for osa_tool.
    """
    if article is None:
        config_loader = ConfigLoader(
            config_dir=os.path.join(
                osa_project_root(), "osa_tool", "config", "standart"
            )
        )
    else:
        config_loader = ArticleConfigLoader(
            config_dir=os.path.join(
                osa_project_root(), "osa_tool", "config", "with_article"
            )
        )

    config_loader.config.git = GitSettings(repository=repo_url)
    config_loader.config.llm = config_loader.config.llm.model_copy(
        update={"api": api, "model": model_name, "url": url}
    )
    logger.info("Config successfully updated and loaded")
    return config_loader


if __name__ == "__main__":
    api = "openai"  # openai, vsegpt
    base_url = "https://api.vsegpt.ru/v1"  # gpt-3.5-turbo, openai/gpt-3.5-turbo

    # model_name = "qwen/qwen-2.5-72b-structured" # "anthropic/claude-3.7-sonnet" # "google/gemma-3-27b-it" # "openai/gpt-4.1" #"openai/gpt-3.5-turbo-1106"
    model_names = [
        # "qwen/qwen-2.5-72b-structured",
        # "anthropic/claude-3.7-sonnet",
        # "google/gemma-3-27b-it",
        "openai/gpt-4.1",
    ]

    repo_name_to_url = dict()

    readme_agent_model_name = "openai/gpt-4.1"

    splits = {
        "train": "data/train-00000-of-00001.parquet",
        "test": "data/test-00000-of-00001.parquet",
    }

    df = pd.read_csv("final_readme_eval-test_repo_name_commit.csv")

    dataset_dir = Path("readme_datasets")
    dataset_dir.mkdir(exist_ok=True, parents=True)

    for i, row in df.iterrows():
        repo_name, repo_commit, repo_url = row
        params = parse_github_url(repo_url)
        if params:
            user, repo, commit = params.groups()
        else:
            continue
        full_url = f"https://api.github.com/repos/{user}/{repo}/git/trees/{commit}?recursive=1"
        repository_url = repo_url.split("/tree/")[0]

        repo_name_to_url[repo_name] = repository_url
        try:
            if not Path(dataset_dir, f"{repo_name}_README.md").exists():
                # Generate readme by OSA
                github_agent = GithubAgent(repository_url)
                github_agent.clone_repository()
                if Path(repo_name, 'readme.md').exists():
                    orig_readme = Path(repo_name, "readme.md")    
                else:
                    orig_readme = Path(repo_name, "README.md")
                shutil.move(orig_readme, Path(dataset_dir, f"{repo_name}_original_README.md"))
                readme_agent(
                    load_configuration(
                        repository_url,
                        api,
                        readme_agent_model_name,
                        base_url,
                        None,
                    ),
                    None,
                )
                src = Path(repo_name, "README.md")
                dst = dataset_dir / f"{repo_name}_README.md"
                shutil.move(src, dst)
                shutil.rmtree(repo_name)
                logger.info(f"Readme file was successfully created and moved into {dst}")
            
            # Generate structure json file
            if not Path(dataset_dir, f"{repo_name}_struct.json").exists():
                headers = {
                    "Accept": "application/vnd.github.v3+json"
                }
                if GITHUB_TOKEN:
                    headers["Authorization"] = f"token {GITHUB_TOKEN}"

                try:
                    r = requests.get(full_url, headers=headers)
                    if r.status_code == 200:
                        with open(f"{dataset_dir}/{repo_name}_struct.json", "w", encoding="utf-8") as f:
                            f.write(r.text)
                            logger.info(f'{dataset_dir}/{repo_name}_struct.json saved successfully')
                        with open(f"{dataset_dir}/{repo_name}_struct.json", "r", encoding="utf-8") as f:
                            f = json.load(f)
                        os.remove(f"{dataset_dir}/{repo_name}_struct.json")
                        stop_words = ['assets', 'results', 'sources', 'packages', 'images', 'data']
                        paths = [
                            entry['path']
                            for entry in f.get('tree', [])
                            if not any(f"/{stop}/" in f"/{entry['path']}/" or entry['path'].startswith(f"{stop}/") for stop in stop_words)
                        ]
                        tree = build_tree(paths)
                        struct = tree_to_dict(tree)
                        with open(f"{dataset_dir}/{repo_name}_struct.json", "w", encoding="utf-8") as f:
                            json.dump(struct, f, indent=4, ensure_ascii=False)
                    else:
                        logger.info(f"[{r.status_code}] Error for {full_url}")           
                except Exception as e:
                    logger.error(f"Request failed for {full_url}: {e}")
        except Exception as e:
            logger.error(f"Error {repr(e)} occured during readme generation for {repo_name}")
        
        # print()

    # if not Path("reflex", "README.md").exists():
    #     github_agent = GithubAgent("https://github.com/reflex-dev/reflex")
    #     github_agent.clone_repository()

    #     readme_agent(
    #         load_configuration(
    #             "https://github.com/reflex-dev/reflex",
    #             api,
    #             readme_agent_model_name,
    #             base_url,
    #             None,
    #         ),
    #         None,
    #     )

    for model_name in model_names:
        prompt = (
            "Determine whether the AI-generated Readme file (ACUTAL_OUTPUT) is better than the original one (EXPECTED_OUTPUT)."
            "ACTUAL_OUTPUT contains two fields: 'readme', which contains generated README itself, "
            "and 'repo_structure' which is json with repository's structure."
            "Generated README's content must be consistent with provided repository structure."
            "The ACTUAL_OUTPUT is not neccessary has to be the same as EXPECTED_OUTPUT,"
            "Your goal is to determine which text is better, using provided Evaluations steps. "
            "The closer score to 1.0 the better AI-generated README file is compared to original one. "
            "Readme structure does not matter much as long as it passes evaluation steps."
        )
        model = CustomLLM(api, model_name, base_url, prompt=prompt)

        config_loader = ConfigLoader(
            config_dir=os.path.join(
                osa_project_root(), "osa_tool", "config", "standart"
            )
        )
        config_loader.config.llm = config_loader.config.llm.model_copy(
            update={"api": api, "model": model_name, "url": base_url}
        )
        base_model = ModelHandlerFactory.build(config_loader.config)

        metrics_init_params = {
            "model": model,
            "verbose_mode": True,
            "async_mode": False,
        }

        readme_correctness_metric = GEval(
            name="Readme quality",
            criteria="Determine whether the generated Readme file is better than original one. ",
            evaluation_steps=[
                "Step 1: Does provided structure of the repository addresses README content?",
                "Step 2: Does the README provide a clear and accurate overview of the repository's purpose?",
                "Step 3: Are installation and setup instructions included and easy to follow?",
                "Step 4: Are usage examples provided and do they clearly demonstrate functionality?",
                "Step 5: Are dependencies or requirements listed appropriately?",
                "Step 6: Is the README easy to read, well-structured, and free of confusing language?",
                "Step 7: Based on the above, rate the AI-generated README compared to the human-written one on a scale from 1 to 10. for each step",
                "Step 8: Normalize this score to a float between 0 and 1.",
            ],
            evaluation_params=[
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
            **metrics_init_params,
        )

        # Readme assess
        results = defaultdict(list)
        for repo_readme in dataset_dir.glob("*.md"):
            if "_original_" in str(repo_readme):
                continue
            repo_name = str(repo_readme).split("_README.md")[0]
            name = repo_name.split("/")[1]

            struct_pth = f"{repo_name}_struct.json"
            original_readme_pth = repo_name + "_original_README.md"
            
            generated_readme = open(str(repo_readme), "r", encoding="utf8").read()
            original_readme = open(str(original_readme_pth), "r", encoding="utf8").read()
            repo_struct = open(str(struct_pth), "r", encoding="utf8").read()

            readme_prompt = ("You have to generate readme.md file for the repository using provided rules,"
                             "repository structure and link to the repository. The answer must be in markdown format, and be processable as md file."
                             "Generated readme must answer following rules:"
                             "1: Does provided structure of the repository addresses README content?"
                             "2: Does the README provide a clear and accurate overview of the repository's purpose?"
                             "3: Are installation and setup instructions included and easy to follow?"
                             "4: Are usage examples provided and do they clearly demonstrate functionality?"
                             "5: Are dependencies or requirements listed appropriately?"
                             "6: Is the README easy to read, well-structured, and free of confusing language?"
                             )
            readme_prompt += f"Repository url: {repo_name_to_url[name]}; Repository structure: {repo_struct}"
            gpt_readme = base_model.send_request(readme_prompt)

            prompt = {"readme": generated_readme, "repo_structure": repo_struct}
            prompt_gpt = {"readme": gpt_readme, "repo_structure": repo_struct}

            test_case = LLMTestCase(
            input=(
                "Evaluate the AI-generated README file by comparing it to the human-written one"
            ),
                actual_output=json.dumps(prompt),
                expected_output=original_readme,
            )
            test_case_gpt = LLMTestCase(
            input=(
                "Evaluate the AI-generated README file by comparing it to the human-written one"
            ),
                actual_output=json.dumps(prompt_gpt),
                expected_output=original_readme,
            )
            try:
                score = readme_correctness_metric.measure(test_case)
                score_gpt = readme_correctness_metric.measure(test_case_gpt)
            except Exception:
                continue

            results["model"].append(model_name)
            results["name"].append(name)
            results["score"].append(score)
            results["test_case_gpt"].append(score_gpt)
            # print(f"Model name: {model_name};\nScore: {score}")
    df = pd.DataFrame.from_dict(results)
    print(f"OSA mean: {df['score'].mean()}; LLM mean: {df['test_case_gpt'].mean()}")
    df.to_csv("readme_results_gpt_1.csv")


        # with open("reflex/README.md", "r", encoding="utf8") as f:
        #     generated_readme = f.read()

        # with open("test_data/README_orig.md", "r", encoding="utf8") as f:
        #     orig_readme = f.read()

        # with open("data/struct_reflex.json", "r", encoding="utf8") as f:
        #     repo_structure = f.read()

        # prompt = {"readme": generated_readme, "repo_structure": repo_structure}

        # test_case = LLMTestCase(
        #     input=(
        #         "Evaluate the AI-generated README file by comparing it to the human-written one"
        #     ),
        #     actual_output=json.dumps(prompt),
        #     expected_output=orig_readme,
        # )
        # score = readme_correctness_metric.measure(test_case)

        # print(f"Model name: {model_name};\nScore: {score}")

    print()
