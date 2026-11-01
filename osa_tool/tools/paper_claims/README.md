# Paper claims tools

The reusable paper-claims operation lives in `osa_tool.operations.analysis.paper_claims`. The command-line helpers in
this directory are thin utilities around that single-document pipeline.

Full documentation is available in [`docs/paper-claims/index.md`](../../../docs/paper-claims/index.md).

PDF parsing defaults to Mistral OCR through OpenRouter. Cloudflare AI can be selected with `--pdf-parser cloudflare-ai`;
its parser is free, while the configured model completion may still incur normal model usage charges. Both remote
parsers require the paper-claims model profile to use `api = "openai"` and an OpenRouter base URL. The `host` API uses
Codex and ignores `base_url`, so remote parser runs warn and stop before parsing.

Install the full optional feature set before using the PDF batch utilities:

```bash
pip install "osa_tool[paper-claims]"
```

For parsed-section claim extraction through the Python API or `paper_analysis --sections-json`, the lightweight
extra avoids Marker/PDF dependencies:

```bash
pip install "osa_tool[paper-claims-lite]"
```

## Quickstart

Run claim extraction for one PDF:

```bash
python -m osa_tool.tools.paper_claims.batch ./paper.pdf --output-dir paper_claim_results
```

Run a directory of PDFs with smaller chunks and low-VRAM Marker settings:

```bash
python -m osa_tool.tools.paper_claims.batch ./papers \
  --pdf-parser marker \
  --chunk-pages 5 \
  --marker-low-vram \
  --marker-process-isolation
```

Include debug-only deduplication selection data in `claims_legacy.json`:

```bash
python -m osa_tool.tools.paper_claims.batch ./paper.pdf --include-debug
```

Force parser reconversion while still rerunning LLM extraction normally:

```bash
python -m osa_tool.tools.paper_claims.batch ./paper.pdf --force-parser-refresh
```

## Output

Each processed document exports:

- `document.md`
- `sections.json`
- `claims_legacy.json`

By default, legacy JSON contains only `result` and `meta`. When `--include-debug` is used, the debug payload also
contains `debug.step3_selection`.

## Evaluation

Evaluation dependencies are included in the full `paper-claims` extra:

```bash
python -m osa_tool.tools.paper_claims.evaluate --help
python -m osa_tool.tools.paper_claims.aggregate --help
```

## Marker dependency note

`marker-pdf` is declared in the optional `paper-claims-marker` extra and loaded only when Marker is selected. Install
it with `pip install "osa_tool[paper-claims,paper-claims-marker]"`. OSA does not enable Marker's LLM processors.
