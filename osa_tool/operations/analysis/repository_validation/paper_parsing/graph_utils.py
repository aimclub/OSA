import copy
import json


def element_node_id(bbox_idx: int) -> str:
    """Node id for a layout element.

    Defined here rather than in the graph builder so that structural parsing and
    graph construction mint identical ids: ``doc_layout`` stamps this onto each
    element once indices are final, and ``doc_graph`` reuses it verbatim. That is
    what makes ``graph`` nodes addressable back into ``report`` positions.
    """
    return f"elem_{bbox_idx}"


def page_node_id(page_num: int) -> str:
    """Node id for a page."""
    return f"page_{page_num}"


def save_graph(graph: dict, path: str) -> None:
    """Serialize the graph dict to a JSON file.
    Strips ``image_bytes`` from nodes to keep the file small."""
    out = copy.deepcopy(graph)
    for node in out.get("nodes", []):
        node.pop("image_bytes", None)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)


def load_graph(path: str) -> dict:
    """Load a graph JSON file."""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
