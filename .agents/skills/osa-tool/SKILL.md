---
name: osa-tool
description: Use OSA's repository improvement CLI and workflow generator with task-focused defaults. For paper-claim verification against a repository, use osa-paper-analysis.
---

# OSA tool

Use this skill for OSA's interactive repository workflows. Translate the requested outcome into the smallest relevant mode and flags. Ask only for required inputs that are missing; use project defaults for model, sampling, and processing settings unless the user asks to change them.

## Choose a mode

- For README, reports, documentation, code organization, notebook tasks, or general repository improvements, use the interactive repository CLI. Read [repository CLI options](references/repository-cli.md) before building a command.
- For extracting claims and checking them against a repository, use the `osa-paper-analysis` skill. It is analysis-only and takes a paper PDF or claims JSON.

## Operating defaults

- Use the current checkout's CLI with `poetry run python -m osa_tool.run`. Use `poetry run osa-tool` only if the console entry point is installed and works in this environment.
- Prefer the task's direct mode and a small set of relevant flags. Do not reproduce the entire README option table in prompts or ask the user to choose every model setting.
- For general repository work, OSA's default `auto` mode proposes a plan. Review that plan and its inactive actions before continuing. `basic` selects a fixed group of actions; `advanced` allows explicit task flags and interactive editing.
- The general CLI defaults to creating a fork and pull request. For work that should stay local, include both `--no-fork` and `--no-pull-request`. Keep fork/PR behavior only when the user explicitly requests that delivery path.
- Never infer a request to publish a workflow, open-source a package, or create a pull request from a request to analyze or improve a repository. Make the intended remote effects clear before running a command that enables them.
- Do not install dependencies or change credentials/configuration unless requested. If required credentials or optional extras are missing, report the exact requirement and continue with any independent local inspection.
- Report which OSA mode ran, its output path or generated files, and any failed stage. Do not claim completion based only on a command being constructed.

## Reference

Read [repository CLI options](references/repository-cli.md) for scheduler modes, task flags, Git effects, and workflow configuration.

Use the repository's `osa_tool/config/settings/arguments.yaml` and the selected command's `--help` as the current source of accepted flags. Some older README/FAQ tables describe removed or renamed options; do not copy a flag from a document without checking it against the current CLI.
