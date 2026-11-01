from pathlib import Path

import pytest

from osa_tool.operations.analysis.paper_claims.exceptions import PdfConversionError
from osa_tool.operations.analysis.paper_claims.models import PdfChunk
from osa_tool.operations.analysis.paper_claims.openrouter_converter import (
    OpenRouterDocumentConverter,
    extract_annotation_text,
)


def _response(text: str) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "annotations": [
                        {
                            "type": "file",
                            "file": {
                                "hash": "parsed-file",
                                "content": [
                                    {"type": "text", "text": text},
                                    {"type": "image_url", "image_url": {"url": "data:image/png;base64,x"}},
                                ],
                            },
                        }
                    ]
                }
            }
        ]
    }


def _chunks(tmp_path: Path) -> list[PdfChunk]:
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"%PDF-test")
    chunk = tmp_path / "chunk.pdf"
    chunk.write_bytes(b"%PDF-chunk")
    return [
        PdfChunk(
            path=chunk,
            index=1,
            start_page=1,
            end_page=2,
            source_path=source,
            source_hash="source-hash",
        )
    ]


class FakeHandler:
    def __init__(self, texts: list[str] | None = None):
        self.model_settings = type("Settings", (), {"base_url": "https://openrouter.ai/api/v1"})()
        self.calls: list[tuple[Path, str]] = []
        self.texts = iter(texts or ["# Method\nParsed body"])

    async def async_request_pdf(self, path: Path, parser: str) -> dict:
        self.calls.append((path, parser))
        return _response(next(self.texts))


def test_extract_annotation_text_joins_text_and_ignores_images():
    response = _response("  # Method\nParsed body  ")

    assert extract_annotation_text(response) == "# Method\nParsed body"
    assert extract_annotation_text({"choices": [{"message": {"content": "not parsed text"}}]}) == ""


@pytest.mark.asyncio
async def test_converter_caches_by_parser_and_force_refresh_bypasses_cache(tmp_path):
    chunks = _chunks(tmp_path)
    handler = FakeHandler(["# Method\nMistral body", "# Method\nCloudflare body", "# Method\nRefreshed body"])
    cache_root = tmp_path / "cache"
    mistral = OpenRouterDocumentConverter(handler, "mistral-ocr", cache_root)

    first = await mistral.convert(chunks, show_progress=False)
    cached = await mistral.convert(chunks, show_progress=False)
    cloudflare = await OpenRouterDocumentConverter(handler, "cloudflare-ai", cache_root).convert(
        chunks, show_progress=False
    )
    refreshed = await mistral.convert(chunks, force_refresh=True, show_progress=False)

    assert first.cache_hit is False
    assert cached.cache_hit is True
    assert "Mistral body" in cached.markdown
    assert cloudflare.cache_hit is False
    assert "Cloudflare body" in cloudflare.markdown
    assert refreshed.cache_hit is False
    assert "Refreshed body" in refreshed.markdown
    assert [parser for _, parser in handler.calls] == ["mistral-ocr", "cloudflare-ai", "mistral-ocr"]
    assert first.cache_dir != cloudflare.cache_dir


@pytest.mark.asyncio
async def test_converter_rejects_empty_annotation_text(tmp_path):
    handler = FakeHandler([""])
    converter = OpenRouterDocumentConverter(handler, "mistral-ocr", tmp_path / "cache")

    with pytest.raises(PdfConversionError, match="returned no parsed text annotation"):
        await converter.convert(_chunks(tmp_path), show_progress=False)


@pytest.mark.parametrize("parser", ["mistral-ocr", "cloudflare-ai"])
def test_converter_requires_openrouter_base_url(tmp_path, parser):
    handler = FakeHandler()
    handler.model_settings.base_url = "https://api.openai.com/v1"

    with pytest.raises(PdfConversionError, match="requires an OpenRouter base URL"):
        OpenRouterDocumentConverter(handler, parser, tmp_path / "cache")


@pytest.mark.asyncio
async def test_converter_rejects_missing_file_annotation(tmp_path):
    class MissingAnnotationHandler(FakeHandler):
        async def async_request_pdf(self, path: Path, parser: str) -> dict:
            self.calls.append((path, parser))
            return {"choices": [{"message": {"content": "completion without annotation"}}]}

    converter = OpenRouterDocumentConverter(MissingAnnotationHandler(), "mistral-ocr", tmp_path / "cache")

    with pytest.raises(PdfConversionError, match="returned no parsed text annotation"):
        await converter.convert(_chunks(tmp_path), show_progress=False)
