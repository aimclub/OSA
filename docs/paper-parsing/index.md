# Structured Paper Parsing

A layout-aware, multimodal document processing pipeline for scientific papers (PDF).

By default, OSA extracts paper content as plain text. With structured paper parsing enabled,
the PDF is instead processed as a *visual* document: every page is segmented into layout
elements (titles, paragraphs, figures, tables, formulas, captions), each element is described
by a vision-language model (VLM), and the results are assembled into a document graph that
captures the structure of the paper. The graph is then linearized in correct reading order —
including two-column layouts — so downstream tasks (e.g. experiment extraction during paper
validation) receive text that also describes figures, tables and formulas.

---

## How it works?

The pipeline consists of three stages, implemented in
`osa_tool/operations/analysis/repository_validation/paper_parsing/`:

| Stage | Module | What it does |
|-------|--------|--------------|
| 1. Layout detection | `doc_layout.py` | Renders each PDF page to an image and detects layout elements with the [DocLayout-YOLO](https://huggingface.co/juliozhao/DocLayout-YOLO-DocStructBench) model. Overlapping boxes are merged, captions are attached to their figures/tables, and adjacent paragraphs are concatenated. |
| 2. Multimodal description | `doc_ocr.py` | Sends every element crop (plus a downsampled full-page context image for figures/tables/formulas) to a VLM through an OpenAI-compatible API. The model returns the element's `text` and a `description`. |
| 3. Document graph | `doc_graph.py` | Builds a graph of pages and elements with typed edges: `page_contains`, `reading_order` (column-aware), `section_member` (title → content), `caption_of`, `text_references` ("see Fig. 1" → figure 1) and `next_page`. |

`pipeline.py` runs the three stages and linearizes the graph; `structured_parser.py` wraps it in
`StructuredPaperParser`, the entry point for both ways of using the parser:

- **Standalone**, on any PDF — no repository, no `ConfigManager` and no validation run. This is
  what the batch CLI in `osa_tool/tools/paper_parsing/` drives.
- **Inside paper validation**, where `data_extractor()` exposes the same contract as the default
  plain-text `PdfParser`, so it acts as a drop-in replacement.

---

## Installation

The pipeline needs extra dependencies that are not part of a standard OSA install:

```sh
poetry install --with paper_parsing
```

It also requires the `poppler` system package (used by `pdf2image` to render PDF pages):

```sh
# Debian / Ubuntu
sudo apt-get install poppler-utils

# macOS
brew install poppler
```

The DocLayout-YOLO weights are downloaded automatically from Hugging Face Hub on first run.

---

## Usage

### As a separate pipeline

The batch CLI parses one or more PDF files (or directories of PDFs) on its own:

```sh
python -m osa_tool.tools.paper_parsing.batch ./paper.pdf --output-dir paper_parsing_results
```

Everything not passed on the command line comes from the `[llm.for_validation]` section of the
configuration file (`--config-file` points at a custom one). Available overrides:

| Option | Default | Description |
| --- | --- | --- |
| `--output-dir` | `paper_parsing_results` | Artifacts are written to `<output-dir>/<pdf stem>/`. |
| `--model` | `vlm_model` from the configuration | Vision-language model. |
| `--base-url` | `vlm_base_url` from the configuration | OpenAI-compatible endpoint. |
| `--api-key-env` | `vlm_api_key` / `$OPENAI_API_KEY` | Environment variable holding the API key. |
| `--device` | `cpu` | Device for layout detection: `cpu` or `cuda`. |
| `--conf-threshold` | `0.15` | Layout-detection confidence threshold. |
| `--max-concurrent` | `5` | Concurrent VLM requests. |
| `--downsample-factor` | `6` | Downsampling of the full-page context image. |
| `--render-dpi` | `200` | Page rasterization resolution. |
| `--layout-batch-size` | `4` | Pages sent to the layout model per call. |
| `--vlm-max-retries` | `3` | Retries per element after the first attempt. |
| `--vlm-retry-delay` | `2.0` | Backoff base in seconds (exponential, jittered). |
| `--vlm-timeout` | `120` | Per-request timeout in seconds. |
| `--save-img` | `false` | Keep the rendered element crops on disk. |
| `--include-report` | `false` | Also export the raw layout report. |

### Many papers at once

`async_batch` runs the same pipeline over a whole list of PDFs, awaiting a batch of papers at a time
instead of parsing them one after another:

```sh
python -m osa_tool.tools.paper_parsing.async_batch --from-file papers.txt --batch-size 4 --output-dir out
```

It runs in two phases, and the order between them is a correctness requirement rather than a
scheduling preference:

1. **Layout** — every PDF is detected in turn and its elements written to
   `<output-dir>/<stem>/layout.json`, with the rendered pages beside it in `pages/`.
2. **Describe** — each saved layout is read back and its elements are described by the VLM,
   `--batch-size` papers at a time.

Layout detection is synchronous CPU work that holds the event loop for its entire duration
(measured: 19 seconds solid on a 6-page paper, minutes on a long one). When it ran interleaved with
description, one paper's detection froze the loop while another paper's HTTP requests were in
flight, so those requests were never serviced and timed out — silently costing every paper a prefix
of its text. Detecting everything first means nothing blocks the loop once requests are being made.

Going through disk also bounds memory to one paper's elements at a time, and makes the describe
phase re-runnable without paying for detection again.

It takes the same overrides as `batch`, plus:

| Option | Default | Description |
| --- | --- | --- |
| `--from-file` | — | File with one PDF path (or directory) per line; `#` comments and blanks are skipped. |
| `--batch-size` | `4` | Papers described concurrently per batch. |
| `--phase` | `all` | `layout` to detect only, `describe` to describe an existing layout, `all` for both. |
| `--skip-existing` | `false` | Skip work already on disk: `layout.json` for the layout phase, `document.md` for the describe phase. |
| `--cleanup-pages` | `false` | Delete `pages/` once a paper is described. Saves disk, but a later `--phase describe` then has no full-page context images to send. |
| `--manifest` | `<output-dir>/manifest.json` | Where the per-paper run manifest is written. |

Splitting the phases across separate invocations lets you detect once and describe repeatedly — for
example to re-describe with a different model, or to fill in a run that lost elements:

```sh
python -m osa_tool.tools.paper_parsing.async_batch ./papers --output-dir out --phase layout
python -m osa_tool.tools.paper_parsing.async_batch ./papers --output-dir out --phase describe
```

The describe phase costs roughly half the memory of the layout phase and does not open the PDF at
all. Budget disk for the handoff: roughly the rendered pages (a few MB per page at 200 DPI) plus the
element crops, per paper, until `--cleanup-pages` or manual removal.

Progress is shown as nested bars: a `layout` bar over papers, then a `describing` bar over papers
carrying running ok / skipped / failed counts, and inside each paper a transient per-element bar for
the VLM stage, labelled with the file it belongs to.

The manifest is rewritten after **every** paper, not just at the end, and replaced atomically — so a
run that is killed still leaves an accurate record of what finished. It carries `complete: false`
until the run ends, which is how a partial manifest is told apart from a finished one:

```json
{
  "started_at": "2026-08-20T02:22:03+03:00",
  "updated_at": "2026-08-20T02:22:33+03:00",
  "complete": false,
  "requested": 50,
  "total": 2,
  "ok": 2, "skipped": 0, "failed": 0,
  "elements_requested": 177,
  "elements_described": 176,
  "described_ratio": 0.9944,
  "papers": [
    {"pdf": ".../S0829_2009.11068.pdf", "status": "ok", "output_dir": ".../S0829_2009.11068",
     "duration_seconds": 24.2, "nodes": 140, "edges": 358, "error": null,
     "finished_at": "2026-08-20T02:22:09+03:00"}
  ]
}
```

A paper that fails is recorded in the manifest with its error and the rest of the batch continues; the
exit code is non-zero if anything failed. Because `--max-concurrent` is per paper, the ceiling on
in-flight VLM requests is `batch-size × max-concurrent` — size both against the endpoint's rate limit.
Layout detection itself is synchronous CPU/GPU work, so within a batch it is the description stages
that overlap, not the detection stages.

### Memory

Pages are rasterized to a temporary directory and decoded on demand, so the detection stage holds a
handful of pages rather than the whole document — peak page memory is flat in the page count instead
of linear. If the process is still killed on a memory-tight machine, the levers, in order of effect:

- `--render-dpi 150` (or `120`) — page memory scales with the square of the DPI, so this is the
  largest single lever. It costs detection and description quality on small text.
- `--batch-size 1` in `async_batch` — papers in flight are the other multiplier.
- `--layout-batch-size 2` — fewer pages resident per model call.

### Missing text

`elements_described / elements_requested` in the manifest is the share of layout elements the VLM
actually answered for. A run can report every paper `ok` while most of its text is missing — the
elements still become graph nodes, just empty ones, and the linearizer drops empty blocks from
`document.md`. A ratio well below 1 means requests are failing, not that the paper is short.

Each element is retried `--vlm-max-retries` times with jittered exponential backoff. Retries are
handled in the pipeline rather than by the OpenAI SDK, because the SDK only retries the HTTP statuses
it considers transient and would never retry a `200` with an empty body — which is one of the ways an
element used to lose its text permanently.

`--skip-existing` makes a killed run resumable: papers that already produced a `document.md` are
skipped, so re-running the same command picks up where it stopped.

The same pipeline from Python:

```python
from pathlib import Path

from osa_tool.operations.analysis.repository_validation.paper_parsing import (
    PaperParsingOptions,
    StructuredPaperParser,
)

parser = StructuredPaperParser(
    Path("paper.pdf"),
    vlm_model="qwen/qwen3.6-flash",
    vlm_base_url="https://openrouter.ai/api/v1",
    api_key="<your_api_key>",
    options=PaperParsingOptions(device="cuda", max_concurrent=8),
)
result = parser.parse()                  # or: await parser.aparse()
parser.export(result, "out/paper", include_report=True)
```

`result` is a `PaperParsingResult` holding `markdown`, the layout `report` and the document
`graph`. `StructuredPaperParser.from_model_settings(pdf_path, model_settings)` builds the same
parser from OSA model settings instead, with optional `vlm_model` / `vlm_base_url` / `api_key` /
`options` overrides.

### Inside paper validation

Structured parsing is enabled with the `--structured-paper-parser` flag and is used whenever
a PDF paper is processed during validation:

```sh
python -m osa_tool.run \
  -r https://github.com/user/repository \
  --validate-paper \
  --attachment ./paper.pdf \
  --structured-paper-parser
```

Without the flag, OSA falls back to the default plain-text PDF extraction.

The VLM is called through an OpenAI-compatible API. The key comes from the `vlm_api_key`
setting if it is present, and otherwise from the `OPENAI_API_KEY` environment variable
(see [Configuration](#configuration)).

---

## Configuration

Both the validation flow and the batch CLI read their settings from the `validation` model
settings (`[llm.for_validation]` in the TOML configuration file). All fields are optional and
fall back to the values of the main model configuration; empty values count as unset:

```toml
[llm.for_validation]
# Vision-language model used to describe layout elements.
# Defaults to the model configured for validation (which itself falls back
# to the main [llm] model, "gpt-3.5-turbo" by default).
vlm_model = "qwen/qwen3.6-flash"

# OpenAI-compatible endpoint serving the VLM. Defaults to the configured base_url.
vlm_base_url = "https://openrouter.ai/api/v1"

# API key for the endpoint above, read straight from the configuration.
# Prefer the environment variable below unless the key is safe to keep in the file.
vlm_api_key = "<your_api_key>"

# Name of the environment variable to read the key from when `vlm_api_key` is unset.
# `.env` is loaded first. Defaults to "OPENAI_API_KEY".
vlm_api_key_env = "OPENAI_API_KEY"

# Device for layout detection: "cpu" or "cuda". Defaults to "cpu".
paper_parser_device = "cpu"

# Number of concurrent VLM requests. Defaults to 5.
paper_parser_max_concurrent = 5

# Layout-detection confidence threshold. Defaults to 0.15.
paper_parser_conf_threshold = 0.15

# Downsampling of the full-page context image sent with figures. Defaults to 6.
paper_parser_downsample_factor = 6

# Keep the rendered element crops on disk. Defaults to false.
paper_parser_save_img = false
```

!!! note
    The configured `vlm_model` must support image input. If the model behind your
    default configuration is text-only, set `vlm_model` and `vlm_base_url` explicitly.
    When neither `vlm_model` nor `model` resolves to a name, the parser fails immediately
    with an explanatory error instead of calling the API with an empty model.

---

## Output

The parser returns the paper as a single markdown-like string in reading order:

- **Titles** become `##` headings.
- **Paragraphs** are emitted as plain text.
- **Figures, tables and formulas** are emitted as `[Figure] ...`, `[Table] ...`,
  `[Formula] ...` blocks containing the VLM description, so non-textual content stays
  available to downstream prompts.
- **Captions and footnotes** follow the element they belong to.

`data_extractor()` returns exactly that string. The standalone entry points return the full
`PaperParsingResult` instead, and `StructuredPaperParser.export(...)` (used by the batch CLI)
writes:

| File | Description |
| --- | --- |
| `document.md` | The linearized markdown above. |
| `graph.json` | The document graph, image crops stripped. |
| `report.json` | The raw layout report; only with `include_report=True` / `--include-report`. |

For programmatic use, `build_document_graph()` in `doc_graph.py` returns the full graph as
`{"nodes": [...], "edges": [...], "meta": {...}}`, and `run_graph_building()` builds and
saves it from a previously saved segmentation report.

---

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `ModuleNotFoundError: doclayout_yolo` (or `torch`, `cv2`, `pdf2image`) | Optional dependencies not installed | `poetry install --with paper_parsing` |
| `pdf2image.exceptions.PDFInfoNotInstalledError` | `poppler` is missing | Install the `poppler` system package |
| Empty descriptions / JSON parse warnings | The configured model does not support image input | Set `vlm_model` to a vision-capable model |
| CUDA out of memory | Large PDF on GPU | Set `paper_parser_device = "cpu"` or reduce `paper_parser_max_concurrent` |
