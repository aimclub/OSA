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
    readme_generator_api = "openai" # vsegpt
    readme_generator_url = "https://api.openai.com/v1" #"https://openrouter.ai/api/v1" # "https://api.openai.com/v1" # "https://api.openai.com/v1"  # gpt-3.5-turbo, openai/gpt-3.5-turbo
    readme_generator_model_name = "gpt-4.1" #"google/gemma-3-27b-it" #"google/gemini-2.5-flash" # "deepseek/deepseek-chat-v3-0324" # "anthropic/claude-sonnet-4" #"gpt-4.1" #"anthropic/claude-3.7-sonnet"

    # Model to assess readme quality
    readme_assess_model_name = "gpt-4.1"
    readme_assess_api = "openai"
    readme_assess_url = "https://api.openai.com/v1"

    repo_name_to_url = dict()
    df = pd.read_csv("final_readme_eval-test_repo_name_commit.csv")
    dataset_dir = Path(f"readme_datasets_unlimited_{readme_generator_model_name.split('/')[-1]}")
    dataset_dir.mkdir(exist_ok=True, parents=True)
    git_repo = []

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
                if Path(repo_name, "readme.md").exists():
                    orig_readme = Path(repo_name, "readme.md")
                else:
                    orig_readme = Path(repo_name, "README.md")
                shutil.move(
                    orig_readme, Path(dataset_dir, f"{repo_name}_original_README.md")
                )
                readme_agent(
                    load_configuration(
                        repository_url,
                        readme_generator_api,
                        readme_generator_model_name,
                        readme_generator_url,
                        None,
                    ),
                    None,
                )
                src = Path(repo_name, "README.md")
                dst = dataset_dir / f"{repo_name}_README.md"
                shutil.move(src, dst)
                shutil.rmtree(repo_name)
                logger.info(
                    f"Readme file was successfully created and moved into {dst}"
                )

            # Generate structure json file
            if not Path(dataset_dir, f"{repo_name}_struct.json").exists():
                headers = {"Accept": "application/vnd.github.v3+json"}
                if GITHUB_TOKEN:
                    headers["Authorization"] = f"token {GITHUB_TOKEN}"
                try:
                    r = requests.get(full_url, headers=headers)
                    if r.status_code == 200:
                        with open(
                            f"{dataset_dir}/{repo_name}_struct.json",
                            "w",
                            encoding="utf-8",
                        ) as f:
                            f.write(r.text)
                            logger.info(
                                f"{dataset_dir}/{repo_name}_struct.json saved successfully"
                            )
                        with open(
                            f"{dataset_dir}/{repo_name}_struct.json",
                            "r",
                            encoding="utf-8",
                        ) as f:
                            f = json.load(f)
                        os.remove(f"{dataset_dir}/{repo_name}_struct.json")
                        stop_words = [
                            "assets",
                            "results",
                            "sources",
                            "packages",
                            "images",
                            "data",
                        ]
                        paths = [
                            entry["path"]
                            for entry in f.get("tree", [])
                            if not any(
                                f"/{stop}/" in f"/{entry['path']}/"
                                or entry["path"].startswith(f"{stop}/")
                                for stop in stop_words
                            )
                        ]
                        tree = build_tree(paths)
                        struct = tree_to_dict(tree)
                        with open(
                            f"{dataset_dir}/{repo_name}_struct.json",
                            "w",
                            encoding="utf-8",
                        ) as f:
                            json.dump(struct, f, indent=4, ensure_ascii=False)
                    else:
                        logger.info(f"[{r.status_code}] Error for {full_url}")
                except Exception as e:
                    logger.error(f"Request failed for {full_url}: {e}")
        except Exception as e:
            logger.error(
                f"Error {repr(e)} occured during readme generation for {repo_name}"
            )

    prompt = (
        "Determine whether the AI-generated Readme file (ACUTAL_OUTPUT) is better than the original one (EXPECTED_OUTPUT)."
        "ACTUAL_OUTPUT contains README itself, "
        "and 'repo_structure' which is json with repository's structure."
        "Generated README's content must be consistent with provided repository structure."
        "The ACTUAL_OUTPUT is not neccessary has to be the same as EXPECTED_OUTPUT,"
        "Your goal is to determine which text is better, using provided Evaluations steps. "
        "The closer score to 1.0 the better AI-generated README file is compared to original one. "
        "Readme structure does not matter much as long as it passes evaluation steps."
    )
    config_loader = ConfigLoader()
    config_loader.config.llm = config_loader.config.llm.model_copy(update={"api": readme_generator_api, "model": readme_generator_model_name, "url": readme_generator_url})
    baseline_readme_generator = ModelHandlerFactory.build(config_loader.config)

    readme_assess_model = CustomLLM(readme_assess_api, readme_assess_model_name, readme_assess_url)
    metrics_init_params = {
        "model": readme_assess_model,
        "verbose_mode": True,
        "async_mode": False,
    }
    readme_correctness_metric = GEval(
        name="Readme quality",
        criteria=prompt, #"Determine quality of AI-generated README file by comparing it to the human-written one",
        evaluation_steps=[
            "Step 1: Does provided structure of the repository addresses README content?",
            "Step 2: Does the README provide a clear and accurate overview of the repository's purpose?",
            "Step 3: Are installation and setup instructions included and easy to follow?",
            "Step 4: Are usage examples provided and do they clearly demonstrate functionality?",
            "Step 5: Are dependencies or requirements listed appropriately?",
            "Step 6: Is the README easy to read, well-structured, and free of confusing language?",
            # "Step 7: Based on the above, rate the AI-generated README compared to the human-written one on a scale from 1 to 10. for each step",
            # "Step 7: Average the scores from step 6 and bring it to scale from 0 to 1. The closer the score to 1.0, the better the AI-generated README file is compared to original one.",
            #"Step 7: Normalize this score to a float between 0 and 1.",
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
        if "_original_" in str(repo_readme) or "readmeai-openai" in str(repo_readme):
            continue
        repo_name = str(repo_readme).split("_README.md")[0]
        name = repo_name.split("/")[1]

        struct_pth = f"{repo_name}_struct.json"
        original_readme_pth = repo_name + "_original_README.md"

        readmeai_readme_pth = "readmeai-openai-" + name + ".md"

        readmeai_readme_pth_v2 = "readmeai-openai-" + name + "/" + "r" + ".md"

        try:
            readmeai_readme = open(str(repo_readme.parent / readmeai_readme_pth), "r", encoding="utf8").read()
        except FileNotFoundError:
            readmeai_readme = open(str(repo_readme.parent / readmeai_readme_pth_v2), "r", encoding="utf8").read()
        generated_readme = open(str(repo_readme), "r", encoding="utf8").read()
        original_readme = open(
            str(original_readme_pth), "r", encoding="utf8"
        ).read()
        repo_struct = open(str(struct_pth), "r", encoding="utf8").read()

        keyfeatures_prompt = """Hello! Analyze the codebase for the project {0} and generate a numbered markdown list summarizing its key techincal features.

                            You will be provided with four pieces of information:
                            1. PROJECT NAME: {0}
                            2. DEPENDENCIES: {1}
                            3. DOCUMENTATION: {2}
                            4. FILE CONTENTS: {3}


                            To complete this task, follow these steps:
                            1. Carefully review all the information about the project to understand the key features of the project.
                            2. Craft an enumerated list with a brief description of the project's features.

                            Your response should adhere to the following guidelines:
                            - The list should contain up to 5 items.
                            - Limit your response for each line of the list to 15 words.
                            - Start each feature description on a new line.

                            Present your final list of core_features within <core_features> tags. Here's an example of a well-structured response:

                            <example>
                            <core_features>

                            1. **Feature 1**: Brief description.

                            2. **Feature 2**: Brief description.

                            3. **Feature 3**: Brief description.

                            4. **Feature 4**: Brief description.

                            5. **Feature 5**: Brief description.

                            </core_features>
                            </example>

                            Now, please, analyze the provided project information and generate a concise numbered list following the guidelines above.
                            """
        summary_prompt = """Deliver a succinct summary that highlights the main purpose and \
                            use of the code files provided in regards to the entire codebase architecture. Focus \
                            on what the code achieves, steering clear of technical implementation details. \
                            While generating the summary, reference additional data about the project below: \n

                            CONTEXT DETAILS:
                            ------------------------
                            FILES CONTENT: {0}
                            ------------------------

                            ADDITIONAL INSTRUCTIONS:
                            ------------------------
                            1. Avoid using words like 'This file', 'The file', 'This code', etc.
                            1a. Summary should start with a verb or noun to make it more clear and concise.
                            2. Do not include quotes, code snippets, bullets, or lists in your response.
                            3. RESPONSE LENGTH: 200-250 words.
                            ------------------------

                            Thank you for your hard work!
                            """
        overview_prompt = """
                            You are tasked with analyzing a codebase and providing a concise overview of the software project. Your goal is to create a brief paragraph that captures the project's core use-case, value proposition, and target audience without delving into technical details.

                            You will be provided with two pieces of information:
                            1. PROJECT NAME: {0}
                            2. SUMMARY OF PROJECT'S FILES: {1}

                            To complete this task, follow these steps:
                            1. Carefully review the project name and file summaries to understand the project's purpose and structure.
                            2. Identify the core use-case, value proposition, and target audience based on the information provided.
                            3. Craft a concise paragraph that elegantly presents these key aspects of the project.

                            Your response should adhere to the following guidelines:
                            - Focus on the project's core use-case and value proposition without including technical details.
                            - Exclude technical jargon, code snippets, implementation specifics, quotes, and links.
                            - Limit your response to a maximum of 60 words.

                            Present your final overview within <overview> tags. Here's an example of a well-structured response:

                            <example>
                            <overview>
                            README-AI is a developer tool that automatically generates comprehensive README files for software projects. It streamlines documentation creation across all technical disciplines, offering customization options and supporting multiple languages. This tool aims to improve consistency and efficiency in project documentation for developers of all experience levels.
                            </overview>
                            </example>

                            Now, please, analyze the provided project information and generate a concise overview following the guidelines above.
                            """
        readme_prompt = ("You have to generate readme.md file for the repository using provided rules and repository structure. The readme.md file must contain summary section, overview secton and core features section"
                            f"You have set of rules for each section. For Summary: {summary_prompt}; for core features: {keyfeatures_prompt}; for overview: {overview_prompt}"
                            )
        readme_prompt += f"Repository url: {repo_name_to_url[name]}" # ; Repository structure: {repo_struct}"
        # gpt_readme = baseline_readme_generator.send_request(readme_prompt)

        prompt = {"readme": generated_readme, "repo_structure": repo_struct}
        prompt_gpt = {"readme": readmeai_readme, "repo_structure": repo_struct}

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
            print(f"\n\n{'=' * 12}OSA METRICS{'=' * 12}")
            score = readme_correctness_metric.measure(test_case)
            print(f"\n\n{'=' * 12}BASELINE METRICS{'=' * 12}")
            score_gpt = readme_correctness_metric.measure(test_case_gpt)
        except Exception:
            continue

        results["model"].append(readme_generator_model_name)
        results["name"].append(name)
        results["score"].append(score)
        results["test_case_gpt"].append(score_gpt)
        print(f"Model name: {readme_generator_model_name};\nScore: {score}")
    df = pd.DataFrame.from_dict(results)
    print(f"Generation model: {readme_generator_model_name}; Checking model: {readme_assess_model_name}")
    print(f"OSA mean: {df['score'].mean()}; LLM mean: {df['test_case_gpt'].mean()}")
    df.to_csv(f"TESTING_readme_results_gpt_osa_prompt_extended_dataset__{readme_generator_model_name.split('/')[-1]}.csv")
    print()
