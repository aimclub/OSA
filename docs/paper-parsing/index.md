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

`structured_parser.py` ties the stages together in `StructuredPaperParser`, which exposes the
same `data_extractor()` contract as the default plain-text `PdfParser`, so it acts as a
drop-in replacement inside the paper-validation flow.

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

The VLM is called through an OpenAI-compatible API; the key is read from the
`OPENAI_API_KEY` environment variable by default (see [Configuration](#configuration)).

---

## Configuration

The parser reads its settings from the `validation` model settings
(`[llm.for_validation]` in the TOML configuration file). All fields are optional
and fall back to the values of the main model configuration:

```toml
[llm.for_validation]
# Vision-language model used to describe layout elements.
# Defaults to the model configured for validation (which itself falls back
# to the main [llm] model, "gpt-3.5-turbo" by default).
vlm_model = "qwen/qwen3.5-flash-02-23"

# OpenAI-compatible endpoint serving the VLM. Defaults to the configured base_url.
vlm_base_url = "https://openrouter.ai/api/v1"

# Name of the environment variable holding the API key. Defaults to "OPENAI_API_KEY".
vlm_api_key_env = "OPENAI_API_KEY"

# Device for layout detection: "cpu" or "cuda". Defaults to "cpu".
paper_parser_device = "cpu"

# Number of concurrent VLM requests. Defaults to 5.
paper_parser_max_concurrent = 5
```

!!! note
    The configured `vlm_model` must support image input. If the model behind your
    default configuration is text-only, set `vlm_model` and `vlm_base_url` explicitly.

---

## Output

The parser returns the paper as a single markdown-like string in reading order:

- **Titles** become `##` headings.
- **Paragraphs** are emitted as plain text.
- **Figures, tables and formulas** are emitted as `[Figure] ...`, `[Table] ...`,
  `[Formula] ...` blocks containing the VLM description, so non-textual content stays
  available to downstream prompts.
- **Captions and footnotes** follow the element they belong to.

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
