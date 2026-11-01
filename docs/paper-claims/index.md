# Paper Claims Pipeline

The paper claims pipeline extracts verifiable technical claims from PDF papers. It is a reusable single-document
operation under `osa_tool.operations.analysis.paper_claims` and is not registered in the legacy scheduler or agent graph.
Use `osa-tool --paper-analysis` when those claims must be verified against a repository. Add
`--include-repository-quality` when the same run also needs the formal repository-quality score.

The PDF flow is:

```text
PDF → physical PDF chunks → selected parser Markdown → structured sections → extracted claims
```

Mistral OCR through OpenRouter is the default parser. Cloudflare AI through OpenRouter and local Marker are selectable
with `pdf_parser` in `[paper_analysis.paper_claims]` or `--pdf-parser`. Cloud parsers require the paper-claims model
profile to use `api = "openai"` with `base_url = "https://openrouter.ai/api/v1"`; `api = "host"` uses Codex and
ignores `base_url`, so the pipeline warns and stops before parsing. OpenRouter parsing runs a small chat completion to
return parsed text in file annotations. Mistral OCR has a
per-page parsing fee; Cloudflare AI parsing is free, though the accompanying model completion may incur normal model
charges. See [OpenRouter's PDF documentation](https://openrouter.ai/docs/guides/overview/multimodal/pdfs) for current
engine pricing and request details.

Callers that already have structured `PaperSection` data can start at claim extraction and avoid the PDF parser,
PDF splitting, and Markdown parsing stages.

## Status

This standalone extraction stage focuses on conversion, section parsing, and claim extraction. The `paper_analysis` CLI
supplies the standard repository-specific integration for the typed result objects.

## Runtime behavior

- PDFs are split with `pypdf` into physical chunks before conversion.
- The default chunk size is five pages and can be changed per run.
- Temporary chunk PDFs are deleted after conversion.
- Successful parser Markdown is cached under the system temporary directory, separately for each parser.
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
result = await pipeline.arun(Path("paper.pdf"), PipelineOptions(pages_per_chunk=5))
```

The synchronous wrapper is available for scripts:

```python
result = pipeline.run(Path("paper.pdf"))
```

Parsed-section inputs use the lighter helper API:

```python
from osa_tool.operations.analysis.artifacts import ModelProvenance
from osa_tool.operations.analysis.paper_claims import (
    export_section_extraction,
    load_sections_json,
    run_claim_extraction_from_sections,
)

loaded = load_sections_json(Path("sections.json"))
extraction = run_claim_extraction_from_sections(model_handler, loaded.sections)
export_section_extraction(
    extraction,
    loaded.sections,
    Path("paper_claims"),
    source_kind="sections_json",
    source_path=loaded.source_path,
    model=ModelProvenance(configured="paper-claim-model", used=["paper-claim-model"]),
)
```

`load_sections_json` accepts either a bare list of `PaperSection` objects or `{ "sections": [...] }`.

The main public objects are:

| Object | Purpose |
| --- | --- |
| `PdfChunker` | Validates and splits PDFs into temporary physical chunks. |
| `MarkerDocumentConverter` | Converts PDF chunks locally through Marker. |
| `OpenRouterDocumentConverter` | Converts chunks through OpenRouter Mistral OCR or Cloudflare AI and caches parsed Markdown. |
| `MarkdownSectionParser` | Parses merged Markdown into ordered `PaperSection` objects. |
| `ClaimExtractor` | Runs section selection, per-section claim extraction, and deduplication. |
| `load_sections_json` | Loads and validates parsed generic `PaperSection` JSON. |
| `run_claim_extraction_from_sections` | Extracts claims from parsed sections without PDF conversion or Markdown parsing. |
| `export_section_extraction` | Writes `claims.json`, `sections.json`, and `report.json` for parsed-section extraction. |
| `PaperClaimPipeline` | Composes the single-document PDF pipeline. |
| `PipelineResult` | Holds converted Markdown, sections, and typed extraction results. |
| `clear_marker_cache` | Deletes Marker cache entries. |

## Exported artifacts

`PaperClaimPipeline.export(...)` writes the full PDF-path artifacts:

| File | Description |
| --- | --- |
| `document.md` | Merged Markdown produced by the selected parser. |
| `sections.json` | Parsed sections with heading metadata. |
| `claims.json` | Typed extraction schema when `legacy=False`. |
| `claims_legacy.json` | MVP-compatible claim JSON when `legacy=True`. |
| `report.json` | Canonical stage report with paper source, configured model, actual successful models, and typed extraction result. |

For parsed-section inputs, `export_section_extraction(...)` writes the same `claims.json`, `sections.json`, and
`report.json` artifacts without `document.md`.

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

## Run through the supported CLI

For repository-backed paper analysis, use [`osa-tool --paper-analysis`](../paper-analysis/index.md). Select a remote
parser or local Marker with `--pdf-parser`:

```bash
osa-tool --paper-analysis \
  --repository https://github.com/example/project \
  --paper ./paper.pdf \
  --pdf-parser cloudflare-ai \
  --paper-output-dir ./analysis
```

Use `--pdf-parser marker` to select the optional local parser. Parser configuration, dependencies, and the supported
CLI options are documented in the [paper-analysis guide](../paper-analysis/index.md).

## Parser cache

Only complete, nonempty parser output is cached. Cache keys include the PDF content hash, chunk page ranges, and parser,
so results from one parser are never reused for another. Incomplete cache entries are ignored and reconverted.

Use `--force-parser-refresh` from the CLI or `PipelineOptions(force_parser_refresh=True)` from Python to bypass the
cache for one run. The previous `--force-marker-refresh` flag remains an alias.

To delete cache entries programmatically:

```python
from osa_tool.operations.analysis.paper_claims import clear_marker_cache

clear_marker_cache()
```

## Optional dependencies

Install the paper-claims extra for PDF conversion through the supported CLI. It includes remote parser support and does
not install Marker:

```bash
pip install "osa_tool[paper-claims]"
```

To select local Marker, install its optional extra as well:

```bash
pip install "osa_tool[paper-claims,paper-claims-marker]"
```

For parsed-section claim extraction without Marker/PDF conversion dependencies, install the lightweight extra:

```bash
pip install "osa_tool[paper-claims-lite]"
```

> **Python compatibility:** core OSA and the remote PDF parsers support Python 3.11 and later. The optional Marker
> parser currently requires Python 3.11--3.14 because its dependency stack is not available for Python 3.15+.

## Dependencies

The `paper-claims-lite` extra provides `rapidfuzz` for parsed-section extraction validation. The `paper-claims` extra
provides PDF splitting and extraction dependencies: `pypdf`, `markdown-it-py`, `rapidfuzz`, `numpy`, `scipy`, and
`sentence-transformers`. The separate `paper-claims-marker` extra installs `marker-pdf`.

Marker, Markdown parsing, PDF splitting, and RapidFuzz validation are loaded lazily when their corresponding stage
runs.
OSA does not enable Marker's LLM processors.

## Module layout

The reusable operation lives in:

```text
osa_tool/operations/analysis/paper_claims/
```

Important modules:

| Module | Responsibility |
| --- | --- |
| `models.py` | Pydantic data contracts and legacy serialization. |
| `io.py` | Generic claims/sections JSON loading and stage-artifact export helpers. |
| `section_extractor.py` | Claim extraction from already parsed sections. |
| `pdf_splitter.py` | PDF validation and physical chunk creation. |
| `marker_converter.py` | Marker conversion, cache handling, and low-VRAM/process-isolated execution. |
| `section_parser.py` | Markdown-to-section parsing. |
| `claim_schemas.py` | Private Pydantic schemas for LLM response validation. |
| `claim_validation.py` | Source-text matching, script guard, and claim candidate partitioning. |
| `claim_input_planner.py` | Token budgets plus hierarchy-aware selection and sentence-aware claim inputs. |
| `claim_deduplicator.py` | Token-bounded, fail-safe LLM claim deduplication. |
| `claim_extractor.py` | LLM request/repair loop and three-step extraction orchestration. |
| `pipeline.py` | Single-document pipeline composition and artifact export. |
