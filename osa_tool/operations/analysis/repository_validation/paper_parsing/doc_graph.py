import os
import re
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

from osa_tool.utils.logger import logger

from osa_tool.operations.analysis.repository_validation.paper_parsing.doc_geometry import (
    centroid as _centroid,
    compute_reading_order_ranks,
    distance as _distance,
    is_content,
    reading_order_key,
)
from osa_tool.operations.analysis.repository_validation.paper_parsing.graph_utils import (
    element_node_id,
    load_graph,
    page_node_id,
    save_graph,
)
from osa_tool.operations.analysis.repository_validation.paper_parsing.graph_patterns import (
    _PARAGRAPH_TYPES,
    _CAPTION_TYPES,
    _ELEM_TYPE_TO_CATEGORY,
    _HEADER_TYPES,
    _CAPTIONABLE_TYPES,
    _REF_PATTERNS,
    _SECTION_MEMBER_TYPES,
)


def _extract_reference_number_from_caption(caption_text: str) -> Optional[int]:
    """Try to pull a number out of a caption string, e.g.
    'Figure 3: Comparison of …' → 3."""
    m = re.search(r"(\d+)", caption_text or "")
    return int(m.group(1)) if m else None


def build_document_graph(
    report: List[dict],
    *,
    header_paragraph_max_distance: float = 150.0,
    header_paragraph_same_page: bool = True,
    add_reading_order: bool = True,
    add_caption_edges: bool = True,
    add_header_paragraph_edges: bool = False,
    add_section_grouping_edges: bool = True,
    section_grouping_cross_page: bool = True,
    add_text_reference_edges: bool = True,
    add_page_sequence_edges: bool = True,
    column_span_ratio: float = 0.8,
    column_gap_ratio: float = 0.2,
) -> dict:
    """Build a graph from the segmentation report.

    Args:
        report (list[dict]): The JSON list produced by ``run_segmentation()``
            (each element is a dict with keys like ``name``, ``page_num``,
            ``box``, ``text``, ``description``, ``confidence``, ``centroid``,
            ``bbox_idx``, …).
        header_paragraph_max_distance (float): Maximum vertical pixel distance
            between a title and a paragraph for them to be linked.
        header_paragraph_same_page (bool): If True, headers and paragraphs are
            only linked when they share the same page.
        add_reading_order (bool): Add ``reading_order`` edges between
            consecutive elements per page.
        add_caption_edges (bool): Add ``caption_of`` edges linking captions to
            their figures / tables.
        add_header_paragraph_edges (bool): Add ``header_paragraph`` edges
            linking headers to nearby paragraphs by vertical distance.
            Disabled by default: it is superseded by the reading-order based
            ``section_member`` edges (see ``add_section_grouping_edges``).
        add_section_grouping_edges (bool): Add ``section_member`` edges linking
            each title to the plain-text / table / figure / formula elements
            that follow it in reading order, until the next title is reached.
        section_grouping_cross_page (bool): If True, a title's section continues
            onto following pages until the next title; if False, grouping is
            restricted to the title's own page.
        add_text_reference_edges (bool): Add ``text_references`` edges linking
            paragraphs to figures / tables mentioned via patterns like "Fig. 1".
        add_page_sequence_edges (bool): Add ``next_page`` edges between
            consecutive page nodes in document order.
        column_span_ratio (float): An element whose box width is at least this
            fraction of the page content width is treated as *spanning* (e.g. a
            section title or full-width figure) rather than belonging to a
            single column.  Used for column-aware reading order.
        column_gap_ratio (float): Minimum horizontal gap between element
            x-centroids — as a fraction of the page content width — for it to be
            recognised as the gutter between two columns.

    Returns:
        dict: ``{"nodes": [...], "edges": [...], "meta": {...}}``
    """

    nodes: Dict[str, dict] = {}  # node_id → node dict
    edges: List[dict] = []  # list of edge dicts

    # Document-global, column-aware reading order; the single source of truth
    # for every ordering-dependent edge builder below.
    order_ranks = compute_reading_order_ranks(
        report,
        span_ratio=column_span_ratio,
        gap_ratio=column_gap_ratio,
    )

    page_nums = sorted({e.get("page_num", 0) for e in report})

    for pn in page_nums:
        nid = page_node_id(pn)
        nodes[nid] = {
            "node_id": nid,
            "node_type": "page",
            "page_num": pn,
            "callers": [],
            "callees": [],
        }

    elem_id_map: Dict[int, str] = {}  # list-index → node_id

    for idx, elem in enumerate(report):
        # ``doc_layout`` stamps ``node_id`` once element positions are final, so
        # reusing it keeps graph nodes addressable back into ``report``. The
        # fallback covers reports built by other means.
        nid = elem.get("node_id") or element_node_id(idx)
        node = dict(elem)  # copy all original keys
        node["node_id"] = nid
        node["node_type"] = "element"
        node["report_index"] = idx
        node["reading_rank"] = order_ranks.get(idx, idx)
        node["is_content"] = is_content(elem)
        node["callers"] = []
        node["callees"] = []
        nodes[nid] = node
        elem_id_map[idx] = nid

    for idx, elem in enumerate(report):
        _add_edge(nodes, edges, page_node_id(elem.get("page_num", 0)), elem_id_map[idx], "page_contains")

    if add_caption_edges:
        _build_caption_edges(report, elem_id_map, nodes, edges)

    if add_header_paragraph_edges:
        _build_header_paragraph_edges(
            report,
            elem_id_map,
            nodes,
            edges,
            max_dist=header_paragraph_max_distance,
            same_page=header_paragraph_same_page,
        )

    if add_section_grouping_edges:
        _build_section_grouping_edges(
            report,
            elem_id_map,
            nodes,
            edges,
            order_ranks,
            cross_page=section_grouping_cross_page,
        )

    if add_text_reference_edges:
        _build_text_reference_edges(report, elem_id_map, nodes, edges, order_ranks)

    if add_reading_order:
        _build_reading_order_edges(report, elem_id_map, nodes, edges, order_ranks)

    if add_page_sequence_edges:
        _build_page_sequence_edges(page_nums, nodes, edges)

    meta = {
        "total_pages": len(page_nums),
        "total_elements": len(report),
        "total_nodes": len(nodes),
        "total_edges": len(edges),
        "edge_type_counts": _count_edge_types(edges),
    }

    return {
        "nodes": list(nodes.values()),
        "edges": edges,
        "meta": meta,
    }


# edge helpers


def _add_edge(
    nodes: Dict[str, dict],
    edges: List[dict],
    source_id: str,
    target_id: str,
    edge_type: str,
    **extra,
) -> None:
    """Create an edge and update callers / callees on both nodes."""
    edge = {
        "source": source_id,
        "target": target_id,
        "edge_type": edge_type,
        **extra,
    }
    edges.append(edge)
    if source_id in nodes:
        nodes[source_id]["callees"].append(target_id)
    if target_id in nodes:
        nodes[target_id]["callers"].append(source_id)


def _count_edge_types(edges: List[dict]) -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for e in edges:
        counts[e["edge_type"]] += 1
    return dict(counts)


# caption linking


def _build_caption_edges(
    report: List[dict],
    elem_id_map: Dict[int, str],
    nodes: Dict[str, dict],
    edges: List[dict],
) -> None:
    """Link caption elements to the figure / table / formula they belong to.

    Structural parsing already resolves this: when ``LayoutExtractor`` folds a
    caption into its element's crop it records the pairing as ``caption_for``.
    That decision is authoritative — it is the one the VLM actually saw, since
    the caption's pixels are inside the element's image — so it is used
    directly. Only captions that structural parsing left unresolved fall back to
    the nearest-captionable heuristic below.
    """

    resolved: set = set()
    for idx, elem in enumerate(report):
        target = elem.get("caption_for")
        if target is None or target not in elem_id_map:
            continue
        resolved.add(idx)
        _add_edge(
            nodes,
            edges,
            elem_id_map[idx],
            elem_id_map[target],
            "caption_of",
            origin="structural",
        )

    page_elements: Dict[int, List[Tuple[int, dict]]] = defaultdict(list)
    for idx, elem in enumerate(report):
        page_elements[elem.get("page_num", 0)].append((idx, elem))

    for elems in page_elements.values():
        captions = [(i, e) for i, e in elems if e.get("name") in _CAPTION_TYPES and i not in resolved]
        targets = [(i, e) for i, e in elems if e.get("name") in _CAPTIONABLE_TYPES]

        for ci, cap in captions:
            cap_center = _centroid(cap)
            best_idx = None
            best_dist = float("inf")
            for ti, tgt in targets:
                d = _distance(cap_center, _centroid(tgt))
                if d < best_dist:
                    best_dist = d
                    best_idx = ti
            if best_idx is not None:
                _add_edge(
                    nodes,
                    edges,
                    elem_id_map[ci],
                    elem_id_map[best_idx],
                    "caption_of",
                    origin="proximity",
                    distance=round(best_dist, 2),
                )


def _build_header_paragraph_edges(
    report: List[dict],
    elem_id_map: Dict[int, str],
    nodes: Dict[str, dict],
    edges: List[dict],
    *,
    max_dist: float = 150.0,
    same_page: bool = True,
) -> None:
    """Link each ``title`` to the closest subsequent ``plain text`` elements
    that are within *max_dist* vertical pixels.

    The heuristic: walk downwards from each header.  Every paragraph whose
    top edge is below the header's bottom edge *and* within ``max_dist`` px
    is linked — until we hit another header or exceed the distance.
    """

    page_elements: Dict[int, List[Tuple[int, dict]]] = defaultdict(list)
    for idx, elem in enumerate(report):
        page_elements[elem.get("page_num", 0)].append((idx, elem))

    for elems in page_elements.values():
        sorted_elems = sorted(elems, key=lambda t: reading_order_key(t[1]))

        current_header_idx: Optional[int] = None
        current_header_bottom: float = 0.0

        for idx, elem in sorted_elems:
            etype = elem.get("name", "")

            if etype in _HEADER_TYPES:
                current_header_idx = idx
                box = elem.get("box", {})
                current_header_bottom = box.get("y2", 0)

            elif etype in _PARAGRAPH_TYPES and current_header_idx is not None:
                box = elem.get("box", {})
                para_top = box.get("y1", 0)
                vdist = para_top - current_header_bottom

                if 0 <= vdist <= max_dist:
                    _add_edge(
                        nodes,
                        edges,
                        elem_id_map[current_header_idx],
                        elem_id_map[idx],
                        "header_paragraph",
                        vertical_distance=round(vdist, 2),
                    )
                elif vdist > max_dist:
                    current_header_idx = None


# section grouping (reading-order based)


def _build_section_grouping_edges(
    report: List[dict],
    elem_id_map: Dict[int, str],
    nodes: Dict[str, dict],
    edges: List[dict],
    order_ranks: Dict[int, int],
    *,
    cross_page: bool = True,
) -> None:
    """Group content elements under the title that heads their section.

    Heuristic (reading-order based, not distance based): walk every element in
    document reading order.  Each time a ``title`` is seen it becomes the
    *current section head*.  Every subsequent content element (plain text,
    table, figure, formula and their captions) is linked to that title with a
    ``section_member`` edge — because they form one uninterrupted reading-order
    sequence after the title — until the next title is reached, which starts a
    new section.

    This generalises the old distance-based ``header_paragraph`` link: tables
    and figures that sit far below their title are still grouped correctly,
    while encountering the next title cleanly terminates the previous section.

    Args:
        cross_page: If True, a section continues onto following pages until the
            next title appears.  If False, only elements on the title's own page
            are grouped (content on a later page with no title of its own is
            left ungrouped).
    """

    # document reading order: pages in order, column-aware reading order within
    # each page (see compute_reading_order_ranks).
    ordered = sorted(range(len(report)), key=lambda i: order_ranks[i])

    current_title_idx: Optional[int] = None
    current_title_page: Optional[int] = None

    for idx in ordered:
        elem = report[idx]
        etype = elem.get("name", "")

        if not is_content(elem):
            continue

        if etype in _HEADER_TYPES:
            current_title_idx = idx
            current_title_page = elem.get("page_num", 0)
            continue

        if current_title_idx is None:
            continue
        if etype not in _SECTION_MEMBER_TYPES:
            continue
        if not cross_page and elem.get("page_num", 0) != current_title_page:
            continue

        _add_edge(
            nodes,
            edges,
            elem_id_map[current_title_idx],
            elem_id_map[idx],
            "section_member",
            member_type=etype,
        )


# text-reference edges (regex)


def _collect_caption_texts(report: List[dict]) -> Dict[int, str]:
    """Map each captionable element index to the caption text describing it.

    Where the number actually lives depends on what structural parsing did.
    When ``LayoutExtractor`` folds a caption into its figure's crop, the caption
    element is left empty and it is the *figure's* own VLM output that contains
    "Figure 3: …" — so the element's own text is the primary source. A separate
    caption element that survived with text of its own is used as well, since it
    is the more precise signal when present.

    Reading the number only from caption elements, as this used to, silently
    yielded nothing for every folded caption and pushed all resolution onto
    positional counting.
    """
    caption_texts: Dict[int, str] = {}

    for idx, elem in enumerate(report):
        if elem.get("name") not in _CAPTIONABLE_TYPES:
            continue
        own_text = (elem.get("text") or "") + " " + (elem.get("description") or "")
        if own_text.strip():
            caption_texts[idx] = own_text

    for idx, elem in enumerate(report):
        if elem.get("name") not in _CAPTION_TYPES:
            continue
        target = elem.get("caption_for")
        if target is None:
            target = _nearest_captionable(report, idx)
        if target is None:
            continue
        cap_text = (elem.get("text") or "") or (elem.get("description") or "")
        if cap_text.strip():
            caption_texts[target] = cap_text

    return caption_texts


def _nearest_captionable(report: List[dict], caption_idx: int) -> Optional[int]:
    """Index of the closest captionable element on the caption's page, if any."""
    caption = report[caption_idx]
    page = caption.get("page_num", 0)
    center = _centroid(caption)

    best_idx: Optional[int] = None
    best_dist = float("inf")
    for idx, elem in enumerate(report):
        if elem.get("page_num", 0) != page or elem.get("name") not in _CAPTIONABLE_TYPES:
            continue
        d = _distance(center, _centroid(elem))
        if d < best_dist:
            best_dist = d
            best_idx = idx
    return best_idx


def _build_text_reference_edges(
    report: List[dict],
    elem_id_map: Dict[int, str],
    nodes: Dict[str, dict],
    edges: List[dict],
    order_ranks: Dict[int, int],
) -> None:
    """Scan every ``plain text`` element's ``text`` field for patterns like
    "Fig. 1", "Table 2", etc.  When a match is found, link the paragraph
    to the *N*-th figure / table / formula in the document (counting in
    reading order).

    Numbering is 1-based and document-global (e.g., "Figure 3" is the 3rd
    figure encountered across all pages).  A declared number found in the
    caption wins; otherwise we fall back to positional counting.
    """

    # --- build lookup: category → ordinal → element index ----------------
    category_by_number: Dict[str, Dict[int, int]] = defaultdict(dict)
    category_positional: Dict[str, List[int]] = defaultdict(list)

    caption_texts = _collect_caption_texts(report)

    # order captionable elements and assign numbers
    all_captionables = [(idx, elem) for idx, elem in enumerate(report) if elem.get("name") in _CAPTIONABLE_TYPES]
    all_captionables.sort(key=lambda t: order_ranks[t[0]])

    positional_counter: Dict[str, int] = defaultdict(int)
    for idx, elem in all_captionables:
        cat = _ELEM_TYPE_TO_CATEGORY.get(elem.get("name", ""), "")
        if not cat:
            continue
        positional_counter[cat] += 1
        category_positional[cat].append(idx)

        cap_text = caption_texts.get(idx, "")
        num = _extract_reference_number_from_caption(cap_text)
        if num is not None:
            category_by_number[cat][num] = idx

    already_linked: set = set()

    for idx, elem in enumerate(report):
        if elem.get("name") not in _PARAGRAPH_TYPES:
            continue
        text = (elem.get("text", "") or "") + " " + (elem.get("description", "") or "")
        if not text.strip():
            continue

        for ref_cat, pattern in _REF_PATTERNS:
            for match in pattern.finditer(text):
                ref_num = int(match.group(1))
                target_idx: Optional[int] = None
                if ref_num in category_by_number.get(ref_cat, {}):
                    target_idx = category_by_number[ref_cat][ref_num]
                elif 1 <= ref_num <= len(category_positional.get(ref_cat, [])):
                    target_idx = category_positional[ref_cat][ref_num - 1]

                if target_idx is not None:
                    pair = (idx, target_idx)
                    if pair not in already_linked:
                        already_linked.add(pair)
                        _add_edge(
                            nodes,
                            edges,
                            elem_id_map[idx],
                            elem_id_map[target_idx],
                            "text_references",
                            matched_pattern=match.group(0),
                            reference_number=ref_num,
                            reference_category=ref_cat,
                        )


def _build_reading_order_edges(
    report: List[dict],
    elem_id_map: Dict[int, str],
    nodes: Dict[str, dict],
    edges: List[dict],
    order_ranks: Dict[int, int],
) -> None:
    """Chain each page's content elements in column-aware reading order (down the
    left column, then the right; see compute_reading_order_ranks).

    Only content elements are chained. Elements structural parsing marked
    ``ignore`` — page furniture, and captions whose pixels were folded into a
    figure — carry no text of their own, so threading them into the chain leaves
    a consumer walking ``reading_order`` stepping through empty nodes.
    """

    page_elements: Dict[int, List[Tuple[int, dict]]] = defaultdict(list)
    for idx, elem in enumerate(report):
        if is_content(elem):
            page_elements[elem.get("page_num", 0)].append((idx, elem))

    for pn in sorted(page_elements):
        elems = sorted(page_elements[pn], key=lambda t: order_ranks[t[0]])
        for i in range(len(elems) - 1):
            _add_edge(
                nodes,
                edges,
                elem_id_map[elems[i][0]],
                elem_id_map[elems[i + 1][0]],
                "reading_order",
            )


def _build_page_sequence_edges(
    page_nums: List[int],
    nodes: Dict[str, dict],
    edges: List[dict],
) -> None:
    """Chain page nodes in document order with ``next_page`` edges."""
    for i in range(len(page_nums) - 1):
        _add_edge(
            nodes,
            edges,
            f"page_{page_nums[i]}",
            f"page_{page_nums[i + 1]}",
            "next_page",
        )


def run_graph_building(
    report_path: str = None,
    output_path: Optional[str] = None,
    **seg_kwargs,
) -> Tuple[List[dict], dict]:
    """Convenience wrapper: runs segmentation then builds the graph.

    Args:
        report_path (str): path to JSON obtained with segmentation
        output_path (str or None): Where to save the graph JSON.
            If None, defaults to ``report_path`` with ``_graph`` suffix.
        **seg_kwargs: Forwarded to ``run_segmentation()`` (e.g. ``device``,
            ``use_api``, ``use_async``, ``max_concurrent``).

    Returns:
        tuple: (report, graph)
    """

    if report_path is None:
        raise NotImplementedError
    else:
        report = load_graph(report_path)

    graph = build_document_graph(report)

    if output_path is None:
        root, _ = os.path.splitext(report_path)
        output_path = f"{root}_graph.json"

    save_graph(graph, output_path)
    logger.info(
        f"Graph saved to {output_path}  "
        f"({graph['meta']['total_nodes']} nodes, "
        f"{graph['meta']['total_edges']} edges)"
    )

    return report, graph
