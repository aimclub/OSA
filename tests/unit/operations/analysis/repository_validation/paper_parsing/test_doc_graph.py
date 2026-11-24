import json
import sys

import pytest

from osa_tool.operations.analysis.repository_validation.paper_parsing import run_graph_building
from osa_tool.operations.analysis.repository_validation.paper_parsing.doc_headers import filter_running_headers
from osa_tool.run import main


def test_build_graph_cli_reads_report_in_column_order(tmp_path, monkeypatch, capsys):
    report = [
        {"name": "title", "text": "Methods", "box": {"x1": 0, "y1": 0, "x2": 100, "y2": 10}},
        {"name": "plain text", "text": "Right", "box": {"x1": 60, "y1": 20, "x2": 100, "y2": 30}},
        {"name": "plain text", "text": "Left first", "box": {"x1": 0, "y1": 20, "x2": 40, "y2": 30}},
        {"name": "plain text", "text": "Left second", "box": {"x1": 0, "y1": 35, "x2": 40, "y2": 45}},
    ]
    for element in report:
        element.update(page_num=1, image_bytes="example crop")

    source = tmp_path / "report.json"
    source.write_text(json.dumps(report), encoding="utf-8")
    destination = tmp_path / "rebuilt"
    monkeypatch.setattr(
        sys,
        "argv",
        ["osa-tool", "--build-paper-graph", str(source), "--paper-parsing-output-dir", str(destination)],
    )

    assert main() == 0
    graph_path = destination / "graph.json"
    assert capsys.readouterr().out.strip() == str(graph_path)
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    ordered = sorted(
        (node for node in graph["nodes"] if node["node_type"] == "element"),
        key=lambda node: node["reading_rank"],
    )
    assert [node["text"] for node in ordered] == ["Methods", "Left first", "Left second", "Right"]
    assert all("image_bytes" not in node for node in ordered)
    assert {edge["edge_type"] for edge in graph["edges"]} >= {"page_contains", "reading_order", "section_member"}


def test_invalid_report_does_not_replace_existing_graph(tmp_path):
    source = tmp_path / "report.json"
    source.write_text('{"nodes": []}', encoding="utf-8")
    destination = tmp_path / "graph.json"
    destination.write_text("original graph", encoding="utf-8")

    with pytest.raises(ValueError, match="a JSON array of layout elements"):
        run_graph_building(source, destination)

    assert destination.read_text(encoding="utf-8") == "original graph"


def test_running_headers_stay_out_of_graph_reading_order(tmp_path):
    report = []
    for page in range(3):
        report.extend(
            [
                {"name": "plain text", "text": f"Journal issue {page}", "page_num": page, "centroid": [30, 10]},
                {"name": "plain text", "text": ["Methods", "Results", "Discussion"][page], "page_num": page},
            ]
        )

    assert filter_running_headers(report, page_height=1000)["removed"] == [0, 2, 4]
    source = tmp_path / "report.json"
    source.write_text(json.dumps(report), encoding="utf-8")
    _, graph = run_graph_building(source)
    content = [node["text"] for node in graph["nodes"] if node.get("is_content")]
    assert content == ["Methods", "Results", "Discussion"]
    assert (tmp_path / "report_graph.json").is_file()
