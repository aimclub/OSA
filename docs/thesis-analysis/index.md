# Thesis Repository Analysis

`thesis_analysis` is OSA's sole CLI-supported pipeline for evaluating a thesis and its repository together. It
deliberately keeps legacy experiment-reproducibility validation, OSA.Edu Streamlit, leaderboard data, and bilingual
PDF layouts outside the core operation.

## Pipeline

```text
repository clone ──> repository quality score
paper PDF ──> paper_claims ──> filtered, batched claim verification ──> canonical JSON + text
claims JSON ───────────────────^
```

- The repository score is produced by the existing `RepositoryQualityScorer.get_quality_report()` contract.
- PDFs use the typed `paper_claims` operation. Install `osa_tool[paper-claims]` for this path.
- Existing `claims.json`, `claims_legacy.json`, and bare claim arrays can start directly at verification.
- By default, only `high` and `medium` verifiability claims reach the model. Low-confidence outcomes are hidden and
  excluded from the implementation rate. Both decisions are recorded in the result.
- Verification is performed in batches of at most 50 claims. Each model result must cover every requested claim index
  exactly once.
- A root `thesis_analysis.json` and `thesis_analysis.txt` are written only after scoring and verification succeed.
  A completed PDF extraction is exported under `paper_claims/`, so it can be supplied to a later run with
  `--claims-json` if verification must be retried.

## Configuration

`config.toml` contains the stable defaults under `[thesis_analysis]`: output directory, selection policy, typed
paper-claims/Marker options, and bounded verification context limits. The formal score weights, result schema, and
verification response contract remain code-level contracts to keep reports comparable.

The three stages select independently overridable models from `[llm.for_repository_quality]`,
`[llm.for_paper_claims]`, and `[llm.for_thesis_verification]`; omitted values inherit `[llm]`. The old
`[llm.for_validation]` profile is rejected with migration guidance.

## CLI

```bash
python -m osa_tool.tools.thesis_analysis \
  --repository https://github.com/example/project \
  --paper ./thesis.pdf \
  --output-dir ./analysis
```

Resume from extracted claims without running Marker:

```bash
python -m osa_tool.tools.thesis_analysis \
  --repository ./project \
  --claims-json ./paper_claims/claims.json \
  --output-dir ./analysis
```

Use `--include-low-verifiability` or `--include-low-confidence` only when the default reporting policy is unsuitable.

The command writes `thesis_analysis.json` and `thesis_analysis.txt`. PDF and UI renderers should consume this canonical
JSON artifact rather than duplicate verification logic.

## Migration from the removed legacy claim flow

`RepositoryQualityScorer` calculates repository quality only. The former PDF parser and claim extractor/verifier were removed;
use this CLI for all thesis claim analysis. The `paper_claims` module's `claims_legacy.json` export remains accepted as
an input adapter for staged runs, but it does not activate the removed legacy flow.
