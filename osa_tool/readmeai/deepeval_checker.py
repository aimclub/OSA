import os
from urllib import response

from deepeval.metrics import GEval
from deepeval.models import DeepEvalBaseLLM
from deepeval.test_case import LLMTestCaseParams

from osa_tool.models.models import ModelHandlerFactory
from osa_tool.readmeai.config.settings import ConfigLoader
from osa_tool.readmeai.ingestion.pipeline import RepositoryProcessor
from osa_tool.utils import osa_project_root




# Class wrapper over vsegpt model class. Uses osa's handlers for initialize vsegpt model class
# Invokes calls to vsegpt instead of openai to assess generated Readme file.
class CustomLLM(DeepEvalBaseLLM):
    def __init__(self, api: str, model_name: str, url: str, prompt: str = "", **kwargs):
        self._system_prompt = prompt
        self.model = self.load_model(api, model_name, url, **kwargs)

    def load_model(self, api: str, model_name: str, base_url: str, **kwargs):
        config_loader = ConfigLoader(
            config_dir=os.path.join(
                osa_project_root(), "osa_tool", "config", "standart"
            )
        )
        config_loader.config.llm = config_loader.config.llm.model_copy(
            update={"api": api, "model": model_name, "url": base_url} | kwargs
        )
        return ModelHandlerFactory.build(config_loader.config)

    def generate(self, prompt: str) -> str:
        prompt = self._system_prompt + prompt
        response = self.model.send_request(prompt)
        return response

    async def a_generate(self, *args, **kwargs) -> str:
        return await super().a_generate(*args, **kwargs)

    def get_model_name(self, *args, **kwargs) -> str:
        return super().get_model_name(*args, **kwargs)


class ReadmeChecker:
    def __init__():
        pass

    def generate(self, readme: str):
        # Gets generated readme and compares it with original readme using LLM models
        pass
