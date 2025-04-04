import os
from typing import Optional

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

from osa_tool.github_agent.github_agent import GithubAgent
from osa_tool.readmeai.config.settings import ConfigLoader, GitSettings
from osa_tool.readmeai.deepeval_checker import CustomLLM
from osa_tool.readmeai.readme_core import readme_agent
from osa_tool.readmeai.readmegen_article.config.settings import ArticleConfigLoader
from osa_tool.utils import osa_project_root


def load_configuration(
        repo_url: str,
        api: str,
        model_name: str,
        url: str, 
        article: Optional[str]
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
            config_dir=os.path.join(osa_project_root(), "osa_tool", "config",
                                    "standart"))
    else:
        config_loader = ArticleConfigLoader(
            config_dir=os.path.join(osa_project_root(), "osa_tool", "config",
                                    "with_article"))

    config_loader.config.git = GitSettings(repository=repo_url)
    config_loader.config.llm = config_loader.config.llm.model_copy(
        update={
            "api": api,
            "model": model_name,
            "url": url
        }
    )
    print("Config successfully updated and loaded")
    return config_loader


if __name__ == "__main__":
    api = "openai"  # openai, vsegpt
    model_name = "openai/gpt-3.5-turbo-1106"
    base_url = "https://api.vsegpt.ru/v1"  # gpt-3.5-turbo, openai/gpt-3.5-turbo
    model = CustomLLM(api, model_name, base_url)

    metrics_init_params = {
        "model": model,
        "verbose_mode": True,
        "async_mode": False,
    }

    readme_correctness_metric = GEval(
        name="readme-checker",
        criteria="Determine whether the generated Readme file is better than original one.",
        evaluation_steps=[""],
        evaluation_params=[
            LLMTestCaseParams.INPUT,
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        **metrics_init_params
    )

    github_agent = GithubAgent("https://github.com/reflex-dev/reflex")
    github_agent.clone_repository()

    readme_agent(load_configuration("https://github.com/reflex-dev/reflex", api, model_name, base_url, None), None)

    with open('README_test.md', 'r', encoding='utf8') as f:
        test_readme = f.read()

    print()
