---
name: osa-paper-analysis
description: Run OSA's paper-to-repository claim analysis from a repository and a paper PDF or existing claims JSON, using the focused CLI and project defaults.
---

# OSA paper analysis

Use this skill when asked to assess whether a research paper's technical claims are implemented in a repository, or to run OSA's paper-analysis workflow. Treat it as a conversational front end to OSA's analysis-only CLI: collect the repository and one claim source, choose sensible defaults, and expose advanced settings only when the user asks or the task requires them.

## Inputs

The required inputs are:

- A local repository path or supported remote repository URL.
- Exactly one of a paper PDF or an existing claims JSON file.

Ask only for whichever required input is missing. If the user already has extracted claims, use that JSON directly and avoid PDF conversion. If they provide a PDF, use it as the source and let OSA extract claims before verification.

## Defaults

- Use the focused entry point: `poetry run python -m osa_tool.tools.paper_analysis` from this checkout. It runs the canonical `PaperAnalysisOperation` without the scheduler workflow. Use `osa-tool --paper-analysis` only when the installed command is the practical entry point.
- Let OSA choose its configured output directory unless the user requests a destination. The focused entry point uses `--output-dir PATH`; the main `osa-tool --paper-analysis` entry point uses `--paper-output-dir PATH`.
- Keep formal repository-quality scoring off unless requested; enable it with `--include-repository-quality`.
- Keep the configured conservative verification policy: verify high- and medium-verifiability claims, and hide low-confidence results. Do not add policy flags unless the user asks for broader coverage.
- Do not ask about chunk sizes, batch sizes, Marker settings, or model profiles for an ordinary run. OSA's configuration owns those details.

## Run

Use the PDF route:

```bash
poetry run python -m osa_tool.tools.paper_analysis \
  --repository ./project \
  --paper ./paper.pdf
```

Use existing claims directly:

```bash
poetry run python -m osa_tool.tools.paper_analysis \
  --repository ./project \
  --claims-json ./claims.json
```

When a custom artifact location is requested with the focused command, add `--output-dir ./analysis`; with the main `osa-tool --paper-analysis` command, use `--paper-output-dir ./analysis`. A successful run prints the root `paper_analysis.json` path. Read that JSON and its accompanying `paper_analysis.txt`; use exported stage reports under `paper_claims/`, `claim_verification/`, and optionally `repository_quality/` to explain completed stages. A failing stage normally has no report of its own because reports are exported only after that stage succeeds. Inspect OSA's logs for the failure details; reports from earlier completed stages may still be available.

For PDF extraction, check that the optional paper-claims dependencies are installed (`poetry install --all-extras` for this checkout, or the package's `paper-claims` extra). Do not install dependencies without an explicit request. If the focused command is unavailable, report the concrete setup issue and give the matching invocation rather than silently switching to the broad scheduler CLI.

## Boundaries

This mode clones or reads the target repository and writes analysis artifacts. It does not generate or edit repository files, create forks or pull requests, or run the scheduler. Do not switch to the general `osa-tool` workflow for a paper-analysis request.

For README, report, documentation, notebook, workflow, or other general repository tasks, use the broader `osa-tool` skill.

Do not claim an analysis ran unless the command completed. Report the output path and any failed stage. Treat verification as static repository evidence: describe implementation statuses and evidence from OSA's output, not runtime behavior or experimental correctness.

## Project details

Read [`docs/paper-analysis/index.md`](../../../docs/paper-analysis/index.md) for current CLI behavior and artifact formats when needed. The canonical implementation is `osa_tool/operations/analysis/paper_analysis/`; the focused CLI is `osa_tool/tools/paper_analysis/`.
