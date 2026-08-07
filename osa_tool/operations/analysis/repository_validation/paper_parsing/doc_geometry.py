"""Spatial primitives shared by structural parsing and graph construction.

``doc_layout`` (which merges detected boxes into document elements) and
``doc_graph`` (which turns those elements into a graph) both need to reason
about the same page geometry: where the column gutter is, which elements span
the full width, and in what order a human reads them. Keeping that reasoning
here means the two passes cannot drift apart — the merge step and the graph
step order a page identically.

Every element handled here is a plain dict as produced by
:class:`~...doc_layout.LayoutExtractor`, carrying at least ``box``
(``x1``/``y1``/``x2``/``y2``), ``page_num`` and — once layout has run —
``centroid`` and ``ignore``.
"""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

Item = Tuple[int, dict]


def centroid(elem: dict) -> Tuple[float, float]:
    """Return ``(cx, cy)``, preferring the ``centroid`` key layout already stores."""
    stored = elem.get("centroid")
    if stored:
        return (float(stored[0]), float(stored[1]))
    box = elem.get("box", {})
    return (
        (box.get("x1", 0) + box.get("x2", 0)) / 2.0,
        (box.get("y1", 0) + box.get("y2", 0)) / 2.0,
    )


def distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def reading_order_key(elem: dict) -> Tuple[float, float]:
    """Top-to-bottom, left-to-right sort key *within a single column*.

    For multi-column pages use :func:`compute_reading_order_ranks`, which
    resolves columns first.
    """
    box = elem.get("box", {})
    return (box.get("y1", 0), box.get("x1", 0))


def is_content(elem: dict) -> bool:
    """True for elements that carry document content.

    Elements flagged ``ignore`` are page furniture (headers, page numbers) or
    fragments that structural parsing folded into another element. They must not
    influence layout statistics — a page number in the margin is exactly the
    kind of outlier that used to be mistaken for a column gutter.
    """
    return not elem.get("ignore", False)


def content_span(items: Iterable[Item]) -> Tuple[float, float]:
    """Return ``(left, right)`` of the text block, ignoring page furniture."""
    boxes = [elem.get("box", {}) for _, elem in items if is_content(elem)]
    if not boxes:
        boxes = [elem.get("box", {}) for _, elem in items]
    if not boxes:
        return (0.0, 0.0)
    return (min(b.get("x1", 0) for b in boxes), max(b.get("x2", 0) for b in boxes))


def detect_column_split(
    cxs: List[float],
    content_left: float,
    content_width: float,
    gap_ratio: float,
    *,
    center_band: float = 0.25,
) -> Optional[float]:
    """Find the x coordinate of the gutter between two columns.

    Looks for the widest horizontal gap between consecutive element centroids,
    but only accepts gaps whose midpoint falls in the central
    ``[center_band, 1 - center_band]`` fraction of the content width. A real
    gutter sits near the middle of the text block; the widest gap overall is
    often just an outlier hugging one margin, which would put the entire page
    into a single "column" and scramble the reading order.

    Returns the split x, or ``None`` when the band is single-column.
    """
    if len(cxs) < 2 or content_width <= 0:
        return None

    low = content_left + center_band * content_width
    high = content_left + (1.0 - center_band) * content_width

    best_gap = 0.0
    best_mid: Optional[float] = None
    for a, b in zip(sorted(cxs), sorted(cxs)[1:]):
        mid = (a + b) / 2.0
        if not (low <= mid <= high):
            continue
        gap = b - a
        if gap > best_gap:
            best_gap = gap
            best_mid = mid

    if best_mid is not None and best_gap >= gap_ratio * content_width:
        return best_mid
    return None


def _order_band(band: List[Item], split: Optional[float]) -> List[int]:
    """Order one horizontal band: whole left column, then whole right column."""
    if not band:
        return []
    if split is None:
        return [idx for idx, _ in sorted(band, key=lambda t: reading_order_key(t[1]))]
    left = [t for t in band if centroid(t[1])[0] <= split]
    right = [t for t in band if centroid(t[1])[0] > split]
    left.sort(key=lambda t: reading_order_key(t[1]))
    right.sort(key=lambda t: reading_order_key(t[1]))
    return [idx for idx, _ in left] + [idx for idx, _ in right]


def order_page_elements(
    items: List[Item],
    *,
    span_ratio: float = 0.8,
    gap_ratio: float = 0.2,
) -> List[int]:
    """Return one page's element indices in column-aware reading order.

    Algorithm:
      1. Measure the page from its *content* elements only (see :func:`is_content`)
         — content span, which elements span the full width, and where the gutter
         is. Ignored furniture is placed using those statistics but never shapes
         them.
      2. Spanning elements (box width >= ``span_ratio`` of the content width:
         section titles, full-width figures) act as horizontal separators,
         cutting the page into bands.
      3. Each band is emitted left column then right column; bands and spanning
         elements interleave top-to-bottom.

    On a single-column page no gutter is found and the result is plain
    top-to-bottom order.
    """
    if not items:
        return []

    content_left, content_right = content_span(items)
    content_width = content_right - content_left

    spanning: List[Item] = []
    columnar: List[Item] = []
    for idx, elem in items:
        box = elem.get("box", {})
        width = box.get("x2", 0) - box.get("x1", 0)
        if content_width > 0 and width >= span_ratio * content_width and is_content(elem):
            spanning.append((idx, elem))
        else:
            columnar.append((idx, elem))

    spanning.sort(key=lambda t: centroid(t[1])[1])
    span_ys = [centroid(elem)[1] for _, elem in spanning]

    split = detect_column_split(
        [centroid(elem)[0] for _, elem in columnar if is_content(elem)],
        content_left,
        content_width,
        gap_ratio,
    )

    bands: Dict[int, List[Item]] = defaultdict(list)
    for idx, elem in columnar:
        cy = centroid(elem)[1]
        bands[sum(1 for sy in span_ys if sy < cy)].append((idx, elem))

    order: List[int] = []
    for band_idx in range(len(spanning) + 1):
        order.extend(_order_band(bands.get(band_idx, []), split))
        if band_idx < len(spanning):
            order.append(spanning[band_idx][0])
    return order


def compute_reading_order_ranks(
    report: List[dict],
    *,
    span_ratio: float = 0.8,
    gap_ratio: float = 0.2,
) -> Dict[int, int]:
    """Compute a document-global reading-order rank for every element index.

    Pages are processed in order and laid out with :func:`order_page_elements`.
    The returned ``idx -> rank`` mapping is the single source of truth for every
    ordering-dependent consumer, in both structural parsing and the graph.
    """
    page_elements: Dict[int, List[Item]] = defaultdict(list)
    for idx, elem in enumerate(report):
        page_elements[elem.get("page_num", 0)].append((idx, elem))

    ranks: Dict[int, int] = {}
    rank = 0
    for page_num in sorted(page_elements):
        for idx in order_page_elements(
            page_elements[page_num],
            span_ratio=span_ratio,
            gap_ratio=gap_ratio,
        ):
            ranks[idx] = rank
            rank += 1
    return ranks
