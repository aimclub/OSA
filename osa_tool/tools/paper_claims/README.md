# Paper claims tools

The reusable paper-claims operation lives in `osa_tool.operations.analysis.paper_claims`. The command-line helpers in
this directory are thin utilities around that single-document pipeline.

Full documentation is available in [`docs/paper-claims/index.md`](../../../docs/paper-claims/index.md).

## Quickstart

Run claim extraction for one PDF:

```bash
python -m osa_tool.tools.paper_claims.batch ./paper.pdf --output-dir paper_claim_results
```

Run a directory of PDFs with smaller chunks and low-VRAM Marker settings:

```bash
python -m osa_tool.tools.paper_claims.batch ./papers \
  --chunk-pages 5 \
  --marker-low-vram \
  --marker-process-isolation
```

Include debug-only deduplication selection data in `claims_legacy.json`:

```bash
python -m osa_tool.tools.paper_claims.batch ./paper.pdf --include-debug
```

Force Marker reconversion while still rerunning LLM extraction normally:

```bash
python -m osa_tool.tools.paper_claims.batch ./paper.pdf --force-marker-refresh
```

## Output

Each processed document exports:

- `document.md`
- `sections.json`
- `claims_legacy.json`

By default, legacy JSON contains only `result` and `meta`. When `--include-debug` is used, the debug payload also
contains `debug.step3_selection`.

## Evaluation

Evaluation dependencies are included in the main project dependency files:

```bash
python -m osa_tool.tools.paper_claims.evaluate --help
python -m osa_tool.tools.paper_claims.aggregate --help
```

## Marker dependency note

`marker-pdf` is declared in the project dependency files and loaded lazily at conversion time. OSA does not enable
Marker's LLM processors.
