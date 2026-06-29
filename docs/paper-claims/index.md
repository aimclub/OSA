# Paper Claims Pipeline

The paper claims pipeline extracts verifiable technical claims from PDF papers. It is a reusable single-document
operation under `osa_tool.operations.analysis.paper_claims` and is not registered in the legacy scheduler or agent graph.

The current flow is:

```text
PDF → physical PDF chunks → Marker Markdown → structured sections → extracted claims
```

## Status

This is the first half of the paper-claims workflow. It focuses on conversion, section parsing, claim extraction, and
local evaluation utilities. Downstream comparison or repository-specific integration can be built on top of the typed
result objects.

## Runtime behavior

- PDFs are split with `pypdf` into physical chunks before Marker conversion.
- The default chunk size is ten pages and can be changed per run.
- Temporary chunk PDFs are deleted after conversion.
- Marker Markdown is cached under the system temporary directory.
- Section parsing and LLM claim extraction are intentionally rerun every time.
- LLM responses are validated with Pydantic.
- Invalid claim candidates are repaired through the repair prompt; after the final retry, bad claim candidates are
  dropped so one bad claim does not fail the whole document.
- `original_text` is checked against the source section using exact matching first, then conservative RapidFuzz matching.
- Claims are checked for plausible language script against their source evidence and section context.

## Public Python API

```python
from pathlib import Path

from osa_tool.operations.analysis.paper_claims import PaperClaimPipeline, PipelineOptions

pipeline = PaperClaimPipeline(model_handler)
result = await pipeline.arun(Path("paper.pdf"), PipelineOptions(pages_per_chunk=10))
```

The synchronous wrapper is available for scripts:

```python
result = pipeline.run(Path("paper.pdf"))
```

The main public objects are:

| Object | Purpose |
| --- | --- |
| `PdfChunker` | Validates and splits PDFs into temporary physical chunks. |
| `MarkerDocumentConverter` | Converts PDF chunks through Marker and caches successful Markdown output. |
| `MarkdownSectionParser` | Parses merged Markdown into ordered `PaperSection` objects. |
| `ClaimExtractor` | Runs section selection, per-section claim extraction, and deduplication. |
| `PaperClaimPipeline` | Composes the single-document pipeline. |
| `PipelineResult` | Holds converted Markdown, sections, and typed extraction results. |
| `clear_marker_cache` | Deletes Marker cache entries. |

## Exported artifacts

`PaperClaimPipeline.export(...)` writes:

| File | Description |
| --- | --- |
| `document.md` | Merged Marker Markdown. |
| `sections.json` | Parsed sections with heading metadata. |
| `claims.json` | Typed extraction schema when `legacy=False`. |
| `claims_legacy.json` | MVP-compatible claim JSON when `legacy=True`. |

Legacy JSON excludes debug-only `step3_selection` by default:

```python
payload = result.to_legacy_dict()
```

Use `include_debug=True` when you need deduplication debug data:

```python
payload = result.to_legacy_dict(include_debug=True)
PaperClaimPipeline.export(result, "out/paper", legacy=True, include_debug=True)
```

The debug payload is stored under:

```json
{
  "debug": {
    "step3_selection": []
  }
}
```

## Batch CLI

The batch utility processes one or more PDF files or directories through the single-document pipeline:

```bash
python -m osa_tool.tools.paper_claims.batch ./paper.pdf --output-dir paper_claim_results
```

Useful options:

| Option | Default | Description |
| --- | --- | --- |
| `--chunk-pages` | `10` | Number of PDF pages per physical chunk. |
| `--max-retries` | `5` | LLM response validation and repair attempts. |
| `--model` | `openai/gpt-5.4-mini` | Model name passed through the normal OSA validation model settings. |
| `--include-debug` | `false` | Include debug-only data such as `debug.step3_selection` in `claims_legacy.json`. |
| `--force-marker-refresh` | `false` | Ignore cached Marker Markdown and reconvert PDFs. LLM extraction is still rerun. |
| `--marker-process-isolation` / `--no-marker-process-isolation` | `true` | Run each Marker chunk in a separate Python process to release CUDA memory between chunks. |
| `--marker-low-vram` | `false` | Use conservative Marker batch sizes for low-VRAM GPUs. |
| `--marker-log-cuda-memory` / `--no-marker-log-cuda-memory` | `true` | Log CUDA memory before and after each Marker chunk when CUDA is available. |

Example for a low-VRAM GPU:

```bash
python -m osa_tool.tools.paper_claims.batch ./papers \
  --chunk-pages 5 \
  --marker-low-vram \
  --marker-process-isolation
```

Example with debug selection output:

```bash
python -m osa_tool.tools.paper_claims.batch ./paper.pdf --include-debug
```

## Marker cache

Only successful Marker Markdown is cached. The cache key includes the PDF content hash, chunk size, Marker version, and
relevant conversion options. Incomplete cache entries are ignored and reconverted.

Use `--force-marker-refresh` from the CLI or `MarkerOptions(force_refresh=True)` from Python to bypass the cache for one
run.

To delete cache entries programmatically:

```python
from osa_tool.operations.analysis.paper_claims import clear_marker_cache

clear_marker_cache()
```

## Evaluation utilities

Evaluation dependencies are included in the main project dependency files.

Run semantic matching:

```bash
python -m osa_tool.tools.paper_claims.evaluate \
  --llm paper_claim_results/paper/claims_legacy.json \
  --human annotations.json \
  --output evaluation.json
```

Aggregate evaluation outputs:

```bash
python -m osa_tool.tools.paper_claims.aggregate ./evaluations --output aggregate.csv
```

## Dependencies

The project dependency files include the paper-claims runtime and evaluation dependencies, including `pypdf`,
`markdown-it-py`, `rapidfuzz`, `marker-pdf`, `pandas`, `numpy`, `scipy`, and `sentence-transformers`.

Marker is loaded lazily at conversion time. OSA does not enable Marker's LLM processors.

## Module layout

The reusable operation lives in:

```text
osa_tool/operations/analysis/paper_claims/
```

Important modules:

| Module | Responsibility |
| --- | --- |
| `models.py` | Pydantic data contracts and legacy serialization. |
| `pdf_splitter.py` | PDF validation and physical chunk creation. |
| `marker_converter.py` | Marker conversion, cache handling, and low-VRAM/process-isolated execution. |
| `section_parser.py` | Markdown-to-section parsing. |
| `claim_schemas.py` | Private Pydantic schemas for LLM response validation. |
| `claim_validation.py` | Source-text matching, script guard, and claim candidate partitioning. |
| `claim_extractor.py` | LLM request/repair loop and three-step extraction orchestration. |
| `pipeline.py` | Single-document pipeline composition and artifact export. |

Supporting command-line tools live in:

```text
osa_tool/tools/paper_claims/
```
