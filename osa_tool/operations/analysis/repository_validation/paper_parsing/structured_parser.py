"""Layout-aware, VLM-based PDF parser exposing the same contract as ``PdfParser``.

``StructuredPaperParser`` is a thin adapter over
:class:`~osa_tool.operations.analysis.repository_validation.paper_parsing.pipeline.PaperParsingPipeline`.
It reads its configuration from the ``validation`` :class:`ModelSettings`, runs
the pipeline and returns the linearized markdown, so it can be used as a drop-in
alternative to
``osa_tool.operations.docs.readme_generation.inputs.article_content.PdfParser``
in the paper-validation flow.

Requires the optional ``paper_parsing`` dependency group (``doclayout_yolo``,
``torch``, ``opencv-python``, ``pdf2image`` + the ``poppler`` system package):
install it with ``poetry install --with paper_parsing``.
"""

import os

from osa_tool.config.settings import ModelSettings
from osa_tool.operations.analysis.repository_validation.paper_parsing.models import PaperParsingOptions
from osa_tool.operations.analysis.repository_validation.paper_parsing.pipeline import PaperParsingPipeline


class StructuredPaperParser:
    """Extract a layout-aware textual representation of a PDF paper.

    Configuration is read from the ``validation`` :class:`ModelSettings`. The
    following optional ``extra`` fields (``ModelSettings`` allows extras) tune
    the pipeline; each falls back to a sensible default:

    - ``vlm_model``: vision-language model name (default: ``model_settings.model``).
    - ``vlm_base_url``: OpenAI-compatible base URL (default: ``model_settings.base_url``).
    - ``vlm_api_key_env``: env var holding the API key (default: ``"OPENAI_API_KEY"``).
    - ``paper_parser_device``: ``"cpu"`` or ``"cuda"`` (default: ``"cpu"``).
    - ``paper_parser_max_concurrent``: concurrent VLM calls (default: ``5``).
    """

    def __init__(self, pdf_path: str, model_settings: ModelSettings) -> None:
        self.path = pdf_path
        extras = model_settings.model_extra or {}
        self.__pipeline = PaperParsingPipeline(
            vlm_model=extras.get("vlm_model", model_settings.model),
            vlm_base_url=extras.get("vlm_base_url", model_settings.base_url),
            api_key=os.getenv(extras.get("vlm_api_key_env", "OPENAI_API_KEY")),
            system_prompt=model_settings.system_prompt,
        )
        self.__options = PaperParsingOptions(
            device=extras.get("paper_parser_device", "cpu"),
            max_concurrent=int(extras.get("paper_parser_max_concurrent", 5)),
        )

    def data_extractor(self) -> str:
        """Run the full pipeline and return the document as a single string."""
        return self.__pipeline.run(self.path, self.__options).markdown
