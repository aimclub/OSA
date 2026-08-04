from pathlib import Path

import pytest

from osa_tool.operations.analysis.paper_claims.exceptions import PdfConversionError
from osa_tool.operations.analysis.paper_claims.marker_converter import (
    LOW_VRAM_MARKER_CONFIG,
    MarkerDocumentConverter,
    _effective_marker_config,
)
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


def test_converter_rejects_chunks_from_different_source_documents(tmp_path):
    chunks = make_chunks(tmp_path)
    other_source = tmp_path / "other-paper.pdf"
    other_source.write_bytes(b"%PDF-other")
    mixed_chunks = [
        chunks[0],
        chunks[1].model_copy(update={"source_path": other_source, "source_hash": "different-hash"}),
    ]
    converter = MarkerDocumentConverter(
        lambda _: (object(), lambda rendered: str(rendered), "test"), marker_version="test"
    )

    with pytest.raises(PdfConversionError, match="same source_path and source_hash"):
        converter.convert(mixed_chunks, MarkerOptions(cache_root=tmp_path / "cache"))


def test_custom_converter_factory_requires_explicit_marker_version():
    with pytest.raises(ValueError, match="marker_version is required"):
        MarkerDocumentConverter(lambda _: (object(), lambda rendered: str(rendered), "custom-v1"))


def test_custom_converter_factory_version_must_match_cache_key_version(tmp_path):
    converter = MarkerDocumentConverter(
        lambda _: (object(), lambda rendered: "# Method\nBody", "custom-v2"),
        marker_version="custom-v1",
    )

    with pytest.raises(PdfConversionError, match="used for the cache key"):
        converter.convert(make_chunks(tmp_path), MarkerOptions(cache_root=tmp_path / "cache"))


def test_custom_converter_version_changes_do_not_reuse_stale_cache(tmp_path):
    def factory(version):
        class FakeConverter:
            def __call__(self, path):
                return f"# Method\nConverted with {version}"

        return lambda _options: (FakeConverter(), lambda rendered: rendered, version)

    chunks = make_chunks(tmp_path)
    options = MarkerOptions(cache_root=tmp_path / "cache")

    first = MarkerDocumentConverter(factory("custom-v1"), marker_version="custom-v1").convert(chunks, options)
    second = MarkerDocumentConverter(factory("custom-v2"), marker_version="custom-v2").convert(chunks, options)

    assert first.cache_dir != second.cache_dir
    assert second.cache_hit is False
    assert "Converted with custom-v2" in second.markdown


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


def test_low_vram_marker_config_can_be_overridden():
    options = MarkerOptions(low_vram=True, marker_config={"recognition_batch_size": 2, "custom": "value"})

    config = _effective_marker_config(options)

    assert config["layout_batch_size"] == LOW_VRAM_MARKER_CONFIG["layout_batch_size"]
    assert config["recognition_batch_size"] == 2
    assert config["custom"] == "value"


def test_process_isolation_uses_chunk_worker_without_initializing_shared_converter(tmp_path, monkeypatch):
    calls: list[int] = []

    def fake_worker(self, *, chunk, chunk_count, options, output_path):
        calls.append(chunk.index)
        return f"# Section {chunk.index}\nBody {chunk.index}"

    monkeypatch.setattr(MarkerDocumentConverter, "_convert_chunk_in_subprocess", fake_worker)
    converter = MarkerDocumentConverter(marker_version="test")

    result = converter.convert(
        make_chunks(tmp_path),
        MarkerOptions(cache_root=tmp_path / "cache", process_isolation=True),
    )

    assert calls == [1, 2]
    assert result.cache_hit is False
    assert "# Section 1" in result.markdown


def test_process_isolation_rejects_custom_converter_factory(tmp_path):
    converter = MarkerDocumentConverter(
        lambda _: (object(), lambda rendered: str(rendered), "test"),
        marker_version="test",
    )

    with pytest.raises(PdfConversionError, match="default Marker converter factory"):
        converter.convert(
            make_chunks(tmp_path),
            MarkerOptions(cache_root=tmp_path / "cache", process_isolation=True),
        )
