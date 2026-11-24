"""Running header / footer removal.

Layout detection labels a running header — a journal banner, a preprint notice,
a page-number line — as ``plain text`` on every page, so each copy survives into
the reading order and the linearized document repeats it once per page, often
splitting a paragraph in two. Preprint servers make this especially noisy: a
bioRxiv banner is several hundred characters long.

Detection works on the described report, before the graph is built:

1. Element text is normalized (lower-cased, digits collapsed to ``#``,
   punctuation dropped) so page numbers and dates do not break the match.
2. Elements with near-identical normalized text are grouped.
3. A group is a running header when it appears on at least
   ``max(min_pages, min_share * page_count)`` pages and its copies sit at a
   stable vertical position (spread below ``max_y_spread`` of the page height).

Header elements are flagged ``ignore`` with ``role="running_header"``. This
keeps them out of ``reading_order``, ``section_member`` and the markdown. Where
the header text was glued into another element — a figure crop that reached into
the top margin — it is cut out of that element's text and the element is kept.
"""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Dict, List

from osa_tool.operations.analysis.repository_validation.paper_parsing.doc_geometry import centroid

RUNNING_HEADER_ROLE = "running_header"


def _normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"\d+", "#", text)
    text = re.sub(r"\W+", " ", text)
    return text.strip()


def detect_running_headers(
    report: List[dict],
    page_height: float,
    *,
    similarity: float = 0.9,
    min_share: float = 0.3,
    min_pages: int = 3,
    max_y_spread: float = 0.03,
    max_length: int = 400,
) -> List[List[int]]:
    """Return groups of report indices that are copies of one running header.

    Args:
        report: Described layout elements (each with ``text``, ``box``, ``page_num``).
        page_height: Rendered page height in pixels, to express vertical spread
            as a fraction of the page.
        similarity: Minimum ``SequenceMatcher`` ratio between normalized texts
            for two elements to be copies of the same header.
        min_share: Fraction of pages a group must appear on.
        min_pages: Absolute floor on the number of pages, so short documents
            do not treat any twice-repeated line as a header.
        max_y_spread: Maximum spread of the copies' vertical centres, as a
            fraction of ``page_height``.
        max_length: Normalized texts longer than this are body paragraphs and
            are never considered.
    """
    page_count = len({elem.get("page_num", 0) for elem in report})

    groups: List[Dict] = []  # {"key", "pages", "indices"}
    for idx, elem in enumerate(report):
        key = _normalize(elem.get("text") or "")
        if not key or len(key) > max_length:
            continue
        for group in groups:
            if SequenceMatcher(None, key, group["key"]).ratio() > similarity:
                group["pages"].add(elem.get("page_num", 0))
                group["indices"].append(idx)
                break
        else:
            groups.append({"key": key, "pages": {elem.get("page_num", 0)}, "indices": [idx]})

    threshold = max(min_pages, min_share * page_count)
    headers: List[List[int]] = []
    for group in groups:
        if len(group["pages"]) < threshold:
            continue
        ys = [centroid(report[idx])[1] / page_height for idx in group["indices"]]
        if max(ys) - min(ys) > max_y_spread:
            continue
        headers.append(group["indices"])
    return headers


def filter_running_headers(report: List[dict], page_height: float, **detect_kwargs) -> dict:
    """Flag running headers in ``report`` and cut their text out of other elements.

    Mutates ``report`` in place. ``detect_kwargs`` are forwarded to
    :func:`detect_running_headers`. Returns a summary of what was removed.
    """
    headers = detect_running_headers(report, page_height, **detect_kwargs)

    header_indices: set = set()
    header_texts: List[str] = []
    for indices in headers:
        for idx in indices:
            header_indices.add(idx)
            report[idx].update(ignore=True, role=RUNNING_HEADER_ROLE)
        header_texts.append(max((report[idx]["text"] for idx in indices), key=len))

    stripped: List[int] = []
    for idx, elem in enumerate(report):
        if idx in header_indices or not elem.get("text"):
            continue
        for header_text in header_texts:
            if header_text in elem["text"]:
                elem["text"] = elem["text"].replace(header_text, "").strip()
                stripped.append(idx)

    return {
        "headers": [
            {"text": text[:80], "elements": len(indices), "pages": len({report[i].get("page_num", 0) for i in indices})}
            for text, indices in zip(header_texts, headers)
        ],
        "removed": sorted(header_indices),
        "text_stripped_from": stripped,
    }
