from pathlib import Path

import pytest

from osa_tool.operations.analysis.paper_claims.exceptions import PdfConversionError
from osa_tool.operations.analysis.paper_claims.marker_converter import MarkerDocumentConverter
from osa_tool.operations.analysis.paper_claims.models import MarkerOptions, PdfChunk


def make_chunks(tmp_path: Path) -> list[PdfChunk]:
    source = tmp_path / "paper.pdf"
    source.write_bytes(b"%PDF-test")
    chunks = []
    for index in (1, 2):
        path = tmp_path / f"chunk-{index}.pdf"
        path.write_bytes(b"chunk")
        chunks.append(
            PdfChunk(
                path=path,
                index=index,
                start_page=(index - 1) * 10 + 1,
                end_page=index * 10,
                source_path=source,
                source_hash="abc123",
            )
        )
    return chunks


def test_converter_reuses_one_instance_and_then_uses_cache(tmp_path):
    calls: list[str] = []
    factory_calls = 0

    class FakeConverter:
        def __call__(self, path):
            calls.append(path)
            return f"# Section {len(calls)}\nBody {len(calls)}"

    def factory(_options):
        nonlocal factory_calls
        factory_calls += 1
        converter = FakeConverter()
        return converter, lambda rendered: rendered, "test"

    options = MarkerOptions(cache_root=tmp_path / "cache")
    converter = MarkerDocumentConverter(factory, marker_version="test")
    chunks = make_chunks(tmp_path)

    first = converter.convert(chunks, options)
    second = converter.convert(chunks, options)

    assert len(calls) == 2
    assert factory_calls == 1
    assert first.cache_hit is False
    assert second.cache_hit is True
    assert "# Section 1" in second.markdown
    assert (first.cache_dir / "COMPLETE").exists()


def test_converter_does_not_accept_partial_empty_output(tmp_path):
    class FakeConverter:
        def __call__(self, path):
            return ""

    converter = MarkerDocumentConverter(
        lambda _: (FakeConverter(), lambda rendered: rendered, "test"), marker_version="test"
    )
    with pytest.raises(PdfConversionError, match="empty output"):
        converter.convert(make_chunks(tmp_path), MarkerOptions(cache_root=tmp_path / "cache"))


def test_incomplete_cache_and_force_refresh_reconvert(tmp_path):
    calls = 0

    class FakeConverter:
        def __call__(self, path):
            nonlocal calls
            calls += 1
            return "# Method\nBody"

    converter = MarkerDocumentConverter(
        lambda _: (FakeConverter(), lambda rendered: rendered, "test"), marker_version="test"
    )
    chunks = make_chunks(tmp_path)
    options = MarkerOptions(cache_root=tmp_path / "cache")
    first = converter.convert(chunks, options)
    (first.cache_dir / "COMPLETE").unlink()

    converter.convert(chunks, options)
    converter.convert(chunks, options.model_copy(update={"force_refresh": True}))

    assert calls == 6
