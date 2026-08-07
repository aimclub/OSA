import pytest

pytest.importorskip("doclayout_yolo", reason="paper_parsing optional dependency group is not installed")

import cv2
import numpy as np

from osa_tool.operations.analysis.repository_validation.paper_parsing.doc_pages import PageStore
from osa_tool.operations.analysis.repository_validation.paper_parsing.exceptions import PageRenderError


def make_store(tmp_path, count: int, cache_size: int = 2, owned: bool = False) -> tuple[PageStore, list]:
    """A store over ``count`` distinct pages, each a solid colour keyed to its index."""
    directory = tmp_path / "pages"
    directory.mkdir()
    paths, expected = [], []
    for index in range(count):
        page = np.full((6, 4, 3), index + 1, dtype=np.uint8)
        path = directory / f"page-{index:03d}.png"
        cv2.imwrite(str(path), page)
        paths.append(path)
        expected.append(page)
    return PageStore(paths, cache_size=cache_size, owned_dir=directory if owned else None), expected


def test_pages_are_returned_in_order_as_bgr_arrays(tmp_path):
    store, expected = make_store(tmp_path, 4)

    assert len(store) == 4
    for index, page in enumerate(expected):
        assert np.array_equal(store[index], page)


def test_only_cache_size_pages_are_held_at_once(tmp_path):
    store, _ = make_store(tmp_path, 6, cache_size=2)

    for index in range(6):
        _ = store[index]

    assert len(store._cache) == 2


def test_recently_used_page_survives_eviction(tmp_path):
    store, _ = make_store(tmp_path, 4, cache_size=2)

    store[0]
    store[1]
    store[0]  # refresh page 0, so page 1 is now the eviction candidate
    store[2]

    assert sorted(store._cache) == [0, 2]


def test_negative_indices_and_slices_work_like_a_list(tmp_path):
    store, expected = make_store(tmp_path, 4)

    assert np.array_equal(store[-1], expected[3])
    assert [page.tolist() for page in store[1:3]] == [page.tolist() for page in expected[1:3]]
    assert len(list(store)) == 4


def test_out_of_range_page_is_reported(tmp_path):
    store, _ = make_store(tmp_path, 2)

    with pytest.raises(IndexError, match="out of range"):
        store[5]


def test_unreadable_page_raises_page_render_error(tmp_path):
    store, _ = make_store(tmp_path, 2)
    store._paths[1].write_bytes(b"not an image")

    with pytest.raises(PageRenderError, match="Could not read rendered page 1"):
        store[1]


def test_close_drops_the_cache_and_deletes_the_owned_directory(tmp_path):
    store, _ = make_store(tmp_path, 3, owned=True)
    directory = tmp_path / "pages"
    store[0]

    store.close()

    assert not directory.exists()
    assert len(store) == 0
    assert store._cache == {}


def test_close_is_idempotent_and_works_as_a_context_manager(tmp_path):
    store, _ = make_store(tmp_path, 2, owned=True)

    with store:
        assert len(store) == 2
    store.close()

    assert not (tmp_path / "pages").exists()


def test_a_store_without_an_owned_directory_leaves_the_files_alone(tmp_path):
    store, _ = make_store(tmp_path, 2, owned=False)

    store.close()

    assert (tmp_path / "pages").exists()


def test_a_dropped_store_still_cleans_up_its_directory(tmp_path):
    import gc

    store, _ = make_store(tmp_path, 2, owned=True)
    store[0]
    del store
    gc.collect()

    assert not (tmp_path / "pages").exists()
