"""Entry point for the layout-aware, VLM-based paper parser.

``StructuredPaperParser`` wraps
:class:`~osa_tool.operations.analysis.repository_validation.paper_parsing.pipeline.PaperParsingPipeline`
and can be used two ways:

- **As a standalone pipeline.** Construct it with an explicit VLM connection and
  :class:`PaperParsingOptions`, then call :meth:`parse` / :meth:`aparse` for the
  full :class:`PaperParsingResult` (markdown, layout report and document graph)
  or :meth:`export` to write the artifacts to disk. No repository, no
  ``ConfigManager`` and no validation run are involved; the batch CLI in
  ``osa_tool.tools.paper_parsing.batch`` is built on this path.
- **As a drop-in PDF parser inside paper validation.** :meth:`from_model_settings`
  reads the VLM connection from the ``validation`` :class:`ModelSettings`, and
  :meth:`data_extractor` returns the linearized markdown, matching the contract of
  ``osa_tool.operations.docs.readme_generation.inputs.article_content.PdfParser``.

Requires the optional ``paper_parsing`` dependency group (``doclayout_yolo``,
``torch``, ``opencv-python``, ``pdf2image`` + the ``poppler`` system package):
install it with ``poetry install --with paper_parsing``.
"""

from __future__ import annotations

import os
from pathlib import Path

import dotenv

from osa_tool.config.settings import ModelSettings
from osa_tool.operations.analysis.repository_validation.paper_parsing.models import (
    PaperParsingOptions,
    PaperParsingResult,
)
from osa_tool.operations.analysis.repository_validation.paper_parsing.pipeline import PaperParsingPipeline

DEFAULT_API_KEY_ENV = "OPENAI_API_KEY"


class StructuredPaperParser:
    """Extract a layout-aware textual representation of a PDF paper.

    Args:
        pdf_path: Path to the PDF to parse.
        vlm_model: Vision-language model used to describe layout elements. Must
            support image input.
        vlm_base_url: OpenAI-compatible endpoint serving the VLM.
        api_key: API key for that endpoint.
        system_prompt: System prompt handed to the VLM.
        options: Layout-detection and description tunables.
    """

    def __init__(
        self,
        pdf_path: Path | str,
        *,
        vlm_model: str,
        vlm_base_url: str | None = None,
        api_key: str | None = None,
        system_prompt: str | None = None,
        options: PaperParsingOptions | None = None,
    ) -> None:
        if not vlm_model:
            raise ValueError(
                "No vision-language model configured for structured paper parsing. "
                "Pass vlm_model explicitly, or set `vlm_model` (or `model`) under "
                "[llm.for_validation] in the configuration file."
            )
        self.path = Path(pdf_path)
        self.options = options or PaperParsingOptions()
        self.pipeline = PaperParsingPipeline(
            vlm_model=vlm_model,
            vlm_base_url=vlm_base_url,
            api_key=api_key,
            system_prompt=system_prompt,
        )

    @classmethod
    def from_model_settings(
        cls,
        pdf_path: Path | str,
        model_settings: ModelSettings,
        *,
        vlm_model: str | None = None,
        vlm_base_url: str | None = None,
        api_key: str | None = None,
        options: PaperParsingOptions | None = None,
    ) -> StructuredPaperParser:
        """Build a parser from OSA model settings, with optional overrides.

        The following ``extra`` fields (``ModelSettings`` allows extras) configure
        the parser; explicit arguments win over them, and each falls back to a
        sensible default:

        - ``vlm_model``: vision-language model name (default: ``model_settings.model``).
        - ``vlm_base_url``: OpenAI-compatible base URL (default: ``model_settings.base_url``).
        - ``vlm_api_key``: the API key itself, taken straight from the configuration.
        - ``vlm_api_key_env``: env var to read the key from when ``vlm_api_key`` is
          unset (default: ``"OPENAI_API_KEY"``).

        The :class:`PaperParsingOptions` extras are documented on
        :meth:`options_from_model_settings`.
        """
        extras = model_settings.model_extra or {}
        dotenv.load_dotenv()
        return cls(
            pdf_path,
            vlm_model=vlm_model or extras.get("vlm_model") or model_settings.model,
            vlm_base_url=vlm_base_url or extras.get("vlm_base_url") or model_settings.base_url,
            api_key=api_key
            or extras.get("vlm_api_key")
            or os.getenv(extras.get("vlm_api_key_env") or DEFAULT_API_KEY_ENV),
            system_prompt=model_settings.system_prompt,
            options=options or cls.options_from_model_settings(model_settings),
        )

    @staticmethod
    def options_from_model_settings(model_settings: ModelSettings) -> PaperParsingOptions:
        """Read the per-run tunables from the ``extra`` fields of ``model_settings``.

        Recognized extras, each falling back to the :class:`PaperParsingOptions`
        default: ``paper_parser_device``, ``paper_parser_max_concurrent``,
        ``paper_parser_conf_threshold``, ``paper_parser_downsample_factor``,
        ``paper_parser_save_img``, ``paper_parser_render_dpi`` and
        ``paper_parser_layout_batch_size``. Empty values are treated as unset so a
        placeholder left in the configuration file does not override the default.
        """
        extras = model_settings.model_extra or {}
        defaults = PaperParsingOptions()
        return PaperParsingOptions(
            device=extras.get("paper_parser_device") or defaults.device,
            max_concurrent=int(extras.get("paper_parser_max_concurrent") or defaults.max_concurrent),
            conf_threshold=float(extras.get("paper_parser_conf_threshold") or defaults.conf_threshold),
            downsample_factor=int(extras.get("paper_parser_downsample_factor") or defaults.downsample_factor),
            save_img=bool(extras.get("paper_parser_save_img", defaults.save_img)),
            render_dpi=int(extras.get("paper_parser_render_dpi") or defaults.render_dpi),
            layout_batch_size=int(extras.get("paper_parser_layout_batch_size") or defaults.layout_batch_size),
            vlm_max_retries=int(extras.get("paper_parser_vlm_max_retries") or defaults.vlm_max_retries),
            vlm_retry_delay=float(extras.get("paper_parser_vlm_retry_delay") or defaults.vlm_retry_delay),
            vlm_timeout=float(extras.get("paper_parser_vlm_timeout") or defaults.vlm_timeout),
        )

    def parse_layout(self, destination: Path | str) -> int:
        """Stage 1 alone: detect layout and persist it under ``destination``."""
        return self.pipeline.run_layout(self.path, destination, self.options)

    async def adescribe(self, destination: Path | str) -> PaperParsingResult:
        """Stages 2-3 alone, from the layout saved by :meth:`parse_layout`."""
        return await self.pipeline.arun_describe(destination, self.options, source_path=self.path)

    async def aparse(self) -> PaperParsingResult:
        """Run the full pipeline and return markdown, layout report and graph."""
        return await self.pipeline.arun(self.path, self.options)

    def parse(self) -> PaperParsingResult:
        """Synchronous :meth:`aparse`; not usable inside a running event loop."""
        return self.pipeline.run(self.path, self.options)

    def data_extractor(self) -> str:
        """Run the full pipeline and return the document as a single string."""
        return self.parse().markdown

    @staticmethod
    def export(result: PaperParsingResult, output_dir: Path | str, *, include_report: bool = False) -> Path:
        """Write ``document.md`` / ``graph.json`` (and optionally ``report.json``)."""
        return PaperParsingPipeline.export(result, output_dir, include_report=include_report)
