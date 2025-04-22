import json
import os
from typing import Optional

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams, LLMTestCase

from osa_tool.github_agent.github_agent import GithubAgent
from osa_tool.readmeai.config.settings import ConfigLoader, GitSettings
from osa_tool.readmeai.deepeval_checker import CustomLLM
from osa_tool.readmeai.readme_core import readme_agent
from osa_tool.readmeai.readmegen_article.config.settings import ArticleConfigLoader
from osa_tool.utils import osa_project_root


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
    print("Config successfully updated and loaded")
    return config_loader


if __name__ == "__main__":
    api = "openai"  # openai, vsegpt
    model_name = "openai/gpt-4.1" #"openai/gpt-3.5-turbo-1106"
    base_url = "https://api.vsegpt.ru/v1"  # gpt-3.5-turbo, openai/gpt-3.5-turbo
    prompt = ("Determine whether the AI-generated Readme file (ACUTAL_OUTPUT) is better than the original one (EXPECTED_OUTPUT)."
              "ACTUAL_OUTPUT contains two fields: 'readme', which contains generated README itself, "
              "and 'repo_structure' which is json with repository's structure."
              "Generated README's content must be consistent with provided repository structure."
              "The ACTUAL_OUTPUT is not neccessary has to be the same as EXPECTED_OUTPUT,"
              "Your goal is to determine which text is better, using provided Evaluations steps. "
              "The closer score to 1.0 the better AI-generated README file is compared to original one. "
              "Readme structure does not matter much as long as it passes evaluation steps.")
    model = CustomLLM(api, model_name, base_url, prompt=prompt)

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
            "Step 7: Based on the above, rate the AI-generated README compared to the human-written one on a scale from 1 to 10.",
            "Step 8: Normalize this score to a float between 0 and 1.",
        ],
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        **metrics_init_params,
    )

    github_agent = GithubAgent("https://github.com/reflex-dev/reflex")
    github_agent.clone_repository()

    readme_agent(
        load_configuration(
            "https://github.com/reflex-dev/reflex", api, model_name, base_url, None
        ),
        None,
    )

    with open("reflex/README.md", "r", encoding="utf8") as f:
        generated_readme = f.read()

    with open("test_data/README_orig.md", "r", encoding="utf8") as f:
        orig_readme = f.read()

    with open("data/struct_reflex.json", "r", encoding="utf8") as f:
        repo_structure  = f.read()

    prompt = {"readme": generated_readme, "repo_structure": repo_structure}

    test_case = LLMTestCase(
        input=(
            "Evaluate the AI-generated README file by comparing it to the human-written one"
        ),
        actual_output=json.dumps(prompt),
        expected_output=orig_readme
    )
    score = readme_correctness_metric.measure(test_case)

    print()
