from typing import ClassVar

from readmegen.config.constants import LLMService
from readmegen.config.settings import ConfigLoader
from readmegen.errors import UnsupportedServiceError
from readmegen.ingestion.models import RepositoryContext
from readmegen.models.llama import LLamaHandler
from readmegen.models.base import BaseModelHandler


class ModelFactory:
    """
    Factory class for creating LLM API handler instances.
    """

    _model_map: ClassVar[dict] = {
        LLMService.OLLAMA.value: LLamaHandler,
    }

    @staticmethod
    def get_backend(
            config: ConfigLoader, context: RepositoryContext
    ) -> BaseModelHandler:
        """
            Returns the appropriate LLM API handler based on config.toml.
        """
        llm_service = ModelFactory._model_map.get(config.config.llm.api)

        if llm_service is None:
            raise UnsupportedServiceError(
                f"Unsupported LLM service provided: {config.config.llm.api}",
            )

        return llm_service(config, context)
