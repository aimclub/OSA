# Thesis Repository Analysis

`thesis_analysis` is the canonical OSA operation for evaluating a thesis and its repository together. It deliberately
keeps presentation layers such as OSA.Edu Streamlit, leaderboard data, and bilingual PDF layouts outside the core
operation.

## Pipeline

```text
repository clone ──> VKR quality score
paper PDF ──> paper_claims ──> filtered, batched claim verification ──> canonical JSON + text
claims JSON ───────────────────^
```

- The repository score is produced by the existing `VkrScorer.get_quality_report()` contract.
- PDFs use the typed `paper_claims` operation. Install `osa_tool[paper-claims]` for this path.
- Existing `claims.json`, `claims_legacy.json`, and bare claim arrays can start directly at verification.
- By default, only `high` and `medium` verifiability claims reach the model. Low-confidence outcomes are hidden and
  excluded from the implementation rate. Both decisions are recorded in the result.
- Verification is performed in batches of at most 50 claims. Each model result must cover every requested claim index
  exactly once.

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
