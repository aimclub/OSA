# Structured paper parsing

OSA can detect the layout of a PDF, describe its elements with a vision-language model (VLM), and build a
document graph. The graph captures column-aware reading order, page sequence, section membership,
captions, and references to figures and tables. OSA also writes Markdown in the graph's reading order.

## Parse a PDF

Install the paper-parsing extra and Poppler. For example, install `poppler-utils` on Debian or Ubuntu
or `poppler` with Homebrew on macOS.

```sh
pip install "osa_tool[paper-parsing]"
osa-tool --parse-paper ./paper.pdf --config-file ./paper-parser.toml \
  --paper-parsing-output-dir ./artifacts/paper-parsing/paper
```

Set `OPENAI_API_KEY` for your OpenAI-compatible VLM endpoint and put the model and endpoint in
`paper-parser.toml`. OSA inherits omitted settings from `[llm]`.

```toml
[llm.for_paper_parsing]
vlm_model = "your-vision-model"
vlm_base_url = "https://your-endpoint.example/v1"
paper_parser_device = "cpu"
```

DocLayout-YOLO downloads its weights from Hugging Face Hub on the first run. Set
`paper_parser_device = "cuda"` to use a CUDA device. Set `paper_parser_render_dpi` or
`paper_parser_layout_batch_size` lower if layout detection runs out of memory. Set
`paper_parser_max_concurrent` to limit simultaneous requests to your endpoint. OSA filters
repeated running headers before building the graph. To retain them, set
`paper_parser_filter_running_headers = false`.

| File | Contents |
| --- | --- |
| `document.md` | Reading-order text and descriptions of figures, tables, and formulas. |
| `graph.json` | Page and element nodes, typed edges, and graph metadata. |
| `report.json` | Described layout elements for rebuilding the graph. |

## Build a graph from a saved report

```sh
osa-tool --build-paper-graph ./artifacts/paper-parsing/paper/report.json \
  --paper-parsing-output-dir ./artifacts/paper-parsing/rebuilt
```

This writes `graph.json` from the JSON array of described elements. The graph builder runs with a
standard OSA installation and needs only the report. The output directory for either command
defaults to `artifacts/paper-parsing/<input-stem>`.

## Python API

```python
from osa_tool.operations.analysis.repository_validation.paper_parsing import (
    PaperParsingOptions,
    StructuredPaperParser,
    run_graph_building,
)

parser = StructuredPaperParser(
    "paper.pdf",
    vlm_model="your-vision-model",
    vlm_base_url="https://your-endpoint.example/v1",
    api_key="your-api-key",
    options=PaperParsingOptions(max_concurrent=4),
)
result = parser.parse()  # Use await parser.aparse() inside an event loop.
parser.export(result, "artifacts/paper-parsing/paper", include_report=True)

report, graph = run_graph_building(
    "artifacts/paper-parsing/paper/report.json",
    "artifacts/paper-parsing/rebuilt/graph.json",
)
```

For a staged run, call `parser.parse_layout(destination)` to save detected elements and rendered
pages, then `await parser.adescribe(destination)` to describe them and build the graph. Keep the
saved layout directory until the description stage finishes.
