# Paper Analysis

`paper_analysis` is OSA's canonical analysis-only workflow for extracting technical claims from a paper and verifying
their implementation against an OSA-supported repository. It never invokes scheduler workflows, README generation,
forks, pull requests, repository mutation, Streamlit, leaderboard logic, or PDF presentation.

## Pipeline

```text
repository clone ──> source context ──> filtered, batched claim verification ──> canonical JSON + text
paper PDF ───────> paper_claims ───────^
sections JSON ─> paper_claims ───────^
claims JSON ─────────────────────────^
                       └─ optional formal repository-quality score
```

- PDF input uses the typed `paper_claims` operation. Install `osa_tool[paper-claims]` for this path.
- Parsed section input uses generic `PaperSection` JSON via `--sections-json`, skipping PDF splitting, Marker, and
  Markdown parsing. Install `osa_tool[paper-claims-lite]` for parsed-section claim extraction without the PDF stack.
- Existing `claims.json`, `claims_legacy.json`, and bare claim arrays can start directly at verification.
- Only high- and medium-verifiability claims are verified by default. Low-confidence results are hidden and excluded
  from the implementation rate unless the corresponding CLI policy override is used.
- Verification uses repository source snippets, Jupyter notebook content, CSV/TSV statistics, and strict batches of at
  most 50 claim indices.
- The default run does not construct or call the formal quality scorer. Add `--include-repository-quality` or set
  `include_repository_quality = true` in configuration to produce the existing formal 0--100 report.

Each completed stage writes its own `report.json`. The root `paper_analysis.json` and `paper_analysis.txt` are written
only after every requested stage succeeds. Earlier completed stage reports remain available after a later failure.

## Configuration

`config.toml` contains `[paper_analysis]`, `[paper_analysis.paper_claims]`, and `[paper_analysis.verification]`.
`include_repository_quality` defaults to `false`; command-line quality flags override it for one run.

Models inherit from `[llm]` unless their stage profile supplies an override:

- `[llm.for_paper_claims]` for PDF claim extraction;
- `[llm.for_paper_verification]` for implementation verification;
- `[llm.for_repository_quality]` only when optional quality scoring is enabled.

Use `--model-paper-claims`, `--model-paper-verification`, or `--model-repository-quality` for per-run overrides.
`--paper-claims-prompts-dir` can point at a directory of TOML prompt overrides using the same `[prompts]` keys as
the built-in prompt files; only keys present in that directory are replaced.

Configured defaults are namespaced by clone name outside the repository. A relative `paper_analysis` default becomes
`<clone-parent>/paper_analysis/<clone-name>/`. If this would collide with the clone, OSA uses the sibling
`<clone-parent>/<clone-name>.osa-artifacts/<clone-name>/`. Explicit output paths inside the analyzed repository are
rejected.

## CLI

```bash
osa-tool --paper-analysis \
  --repository https://github.com/example/project \
  --paper ./paper.pdf \
  --paper-output-dir ./analysis
```

Use already parsed generic sections and optional paper-claim prompt overrides:

```bash
osa-tool --paper-analysis \
  --repository https://github.com/example/project \
  --sections-json ./sections.json \
  --paper-claims-prompts-dir ./prompt-overrides \
  --paper-output-dir ./analysis
```

`sections.json` may be either a bare list of `PaperSection` objects or an object shaped as `{"sections": [...]}`.

Include the formal repository score in the same artifact tree:

```bash
osa-tool --paper-analysis \
  --repository https://github.com/example/project \
  --claims-json ./paper_claims/claims.json \
  --include-repository-quality \
  --paper-output-dir ./analysis
```

The focused wrapper uses the same pipeline and calls its output option `--output-dir`:

```bash
python -m osa_tool.tools.paper_analysis \
  --repository ./project \
  --claims-json ./paper_claims/claims.json \
  --output-dir ./analysis
```

Rich progress is sent to stderr and stdout contains only the final root JSON path. For remote repositories,
`--delete-dir` removes only a clone created by the current invocation; local repositories and pre-existing remote
clones are preserved.

## Artifacts

```text
analysis/
  paper_analysis.json
  paper_analysis.txt
  paper_claims/
    report.json
    claims.json
    document.md            # PDF input only
    sections.json          # PDF or sections JSON input
  claim_verification/
    report.json
  repository_quality/      # only with --include-repository-quality
    report.json
    report.txt
```

`paper_analysis.json` uses schema version `1.0`. It always contains `repository_quality`; the value and quality
artifact paths are `null` when scoring is disabled. Model provenance only lists stages that ran. Every stage report
contains source metadata and configured/successful model provenance. Claim source metadata uses `kind` values
`pdf`, `sections_json`, or `claims_json`.
