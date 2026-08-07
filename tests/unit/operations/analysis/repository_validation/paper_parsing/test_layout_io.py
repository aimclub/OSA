import pytest

pytest.importorskip("doclayout_yolo", reason="paper_parsing optional dependency group is not installed")

import json

import cv2
import numpy as np

from osa_tool.operations.analysis.repository_validation.paper_parsing.doc_pages import PageStore
from osa_tool.operations.analysis.repository_validation.paper_parsing.exceptions import LayoutDetectionError
from osa_tool.operations.analysis.repository_validation.paper_parsing.layout_io import (
    layout_exists,
    load_layout,
    save_layout,
)


def make_pages(tmp_path, count=3) -> PageStore:
    directory = tmp_path / "rendered"
    directory.mkdir()
    paths = []
    for index in range(count):
        path = directory / f"page-{index:03d}.png"
        cv2.imwrite(str(path), np.full((6, 4, 3), index + 1, dtype=np.uint8))
        paths.append(path)
    return PageStore(paths, cache_size=2)


def report():
    return [
        {"bbox_idx": 0, "name": "title", "page_num": 0, "image_bytes": b"aGVsbG8="},
        {"bbox_idx": 1, "name": "plain text", "page_num": 1, "image_bytes": b"d29ybGQ="},
    ]


def test_a_saved_layout_round_trips(tmp_path):
    destination = tmp_path / "paper"

    save_layout(report(), make_pages(tmp_path), destination, source_path="paper.pdf", render_dpi=200)
    elements, pages = load_layout(destination)

    assert [element["bbox_idx"] for element in elements] == [0, 1]
    assert [element["name"] for element in elements] == ["title", "plain text"]
    assert len(pages) == 3
    pages.close()


def test_crops_are_stored_as_plain_base64_not_a_bytes_repr(tmp_path):
    destination = tmp_path / "paper"

    save_layout(report(), make_pages(tmp_path), destination, source_path="paper.pdf", render_dpi=200)

    payload = json.loads((destination / "layout.json").read_text())
    assert payload["elements"][0]["image_bytes"] == "aGVsbG8="
    assert payload["version"] == 1
    assert payload["page_count"] == 3


def test_saved_pages_keep_their_order_and_content(tmp_path):
    destination = tmp_path / "paper"
    original = make_pages(tmp_path)
    expected = [original[index].copy() for index in range(len(original))]

    save_layout(report(), original, destination, source_path="paper.pdf", render_dpi=200)
    _, pages = load_layout(destination)

    for index, page in enumerate(expected):
        assert np.array_equal(pages[index], page)
    pages.close()


def test_closing_a_loaded_store_does_not_delete_the_output_pages(tmp_path):
    """The loaded store borrows the output tree; only a temp render owns its files."""
    destination = tmp_path / "paper"
    save_layout(report(), make_pages(tmp_path), destination, source_path="paper.pdf", render_dpi=200)

    _, pages = load_layout(destination)
    pages.close()

    assert (destination / "pages").exists()
    assert len(list((destination / "pages").iterdir())) == 3


def test_a_missing_layout_is_reported_clearly(tmp_path):
    with pytest.raises(LayoutDetectionError, match="does not exist"):
        load_layout(tmp_path / "nothing")


def test_an_unknown_format_version_is_rejected(tmp_path):
    destination = tmp_path / "paper"
    destination.mkdir()
    (destination / "layout.json").write_text(json.dumps({"version": 99, "elements": [{}]}))

    with pytest.raises(LayoutDetectionError, match="Unsupported layout format version"):
        load_layout(destination)


def test_an_empty_layout_is_rejected(tmp_path):
    destination = tmp_path / "paper"
    destination.mkdir()
    (destination / "layout.json").write_text(json.dumps({"version": 1, "elements": []}))

    with pytest.raises(LayoutDetectionError, match="holds no elements"):
        load_layout(destination)


def test_layout_exists_reports_what_is_on_disk(tmp_path):
    assert layout_exists(tmp_path) is False
    save_layout(report(), make_pages(tmp_path), tmp_path / "paper", source_path="p.pdf", render_dpi=200)
    assert layout_exists(tmp_path / "paper") is True
