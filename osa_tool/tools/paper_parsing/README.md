# Structured paper parsing pipeline

The reusable operation lives in `osa_tool.operations.analysis.repository_validation.paper_parsing` and runs as a
standalone, repository-independent pipeline:

```python
from pathlib import Path

from osa_tool.operations.analysis.repository_validation.paper_parsing import (
    PaperParsingOptions,
    StructuredPaperParser,
)

parser = StructuredPaperParser(
    Path("paper.pdf"),
    vlm_model="qwen/qwen3-vl-30b-a3b-instruct",
    vlm_base_url="https://openrouter.ai/api/v1",
    api_key=...,
    options=PaperParsingOptions(device="cuda"),
)
result = parser.parse()          # markdown + layout report + document graph
parser.export(result, "out/paper", include_report=True)
```

Inside the paper-validation flow the parser is built from the `validation` model settings instead, and
`data_extractor()` returns just the linearized markdown, matching the plain-text `PdfParser` contract:

```python
StructuredPaperParser.from_model_settings(pdf_path, model_settings).data_extractor()
```

The batch CLI runs the standalone path over one or more PDF files or directories:

```bash
python -m osa_tool.tools.paper_parsing.batch ./paper.pdf --output-dir paper_parsing_results
```

CLI flags override the configuration: `--model`, `--base-url`, `--api-key-env`, `--device`, `--conf-threshold`,
`--max-concurrent`, `--downsample-factor`, `--render-dpi`, `--layout-batch-size`, `--save-img`, `--include-report`. Everything else comes from the
`[llm.for_validation]` section of the configuration file (`--config-file` to point at a custom one). No repository is
required.

For a whole list of papers, `async_batch` awaits a batch of them at a time instead of parsing one after another:

```bash
python -m osa_tool.tools.paper_parsing.async_batch --from-file papers.txt --batch-size 4 --output-dir out
```

It runs layout detection for every paper first, persisting each to `<output-dir>/<stem>/layout.json` with its
rendered pages, and only then describes them with the VLM `--batch-size` papers at a time. That order matters:
layout detection is synchronous work that freezes the event loop, and running it while another paper's requests were
in flight stranded those requests until they timed out. `--phase layout` / `--phase describe` run the halves
separately, so a corpus can be detected once and described repeatedly.

It accepts the same overrides plus `--from-file` (one PDF path or directory per line), `--batch-size`, `--phase`,
`--cleanup-pages`, `--skip-existing` (resume a partial run) and `--manifest`. Failures are isolated per paper and collected in
`<output-dir>/manifest.json` alongside node/edge counts and timings. The manifest is rewritten atomically after every
paper and carries `complete: false` until the run ends, so a killed run still leaves an accurate record to resume from.
Progress shows as a `layout` bar then a `describing` bar over papers, plus a transient per-element bar inside each
paper. `elements_described / elements_requested` in the manifest reports how much of the corpus the VLM actually
answered for; each element is retried `--vlm-max-retries` times with jittered backoff. `--max-concurrent` is per paper, so the endpoint
sees up to `batch-size × max-concurrent` requests at once.

The layout stack (`doclayout_yolo`, `torch`, `opencv-python`, `pdf2image`) is an optional dependency group and the
DocLayout-YOLO weights are downloaded on first run:

```bash
poetry install --with paper_parsing
sudo apt-get install poppler-utils   # pdf2image needs poppler
```

Pages are rasterized to a temporary directory and decoded on demand rather than held in memory, so peak page memory
depends on the cache size, not the page count. If a run is still OOM-killed, lower `--render-dpi` first (memory scales
with its square), then `--batch-size`, then `--layout-batch-size`, and re-run with `--skip-existing` to resume.
