# Repository CLI and workflow options

Use the main scheduler CLI for repository tasks such as reports, README generation, docstrings, community files, notebook processing, and workflow generation. From this checkout:

```bash
poetry run python -m osa_tool.run --help
poetry run python -m osa_tool.run --repository https://github.com/OWNER/REPO --mode auto --no-fork --no-pull-request
```

The repository and requested action are the main inputs. OSA defaults to `auto`, which analyzes the repository and presents a proposed task plan for confirmation or interactive editing. `basic` runs a fixed set of actions (About section, community docs, organization, README, and report). `advanced` starts from explicit flags and lets the interactive plan editor refine them. Review the plan before allowing execution.

## Common task flags

Choose only flags that match the user's request:

| Goal | Flags |
| --- | --- |
| Repository report | `--report`; optionally `--scorecard` to add OpenSSF Scorecard results to the report |
| README | `--readme` |
| Community docs | `--community-docs` |
| Requirements file | `--requirements` |
| Python docstrings | `--docstring`; optionally `--incremental` and `--target-files PATH...` |
| Notebook report | `--notebook-report [PATH...]`; no paths means scan the repository notebooks |
| Notebook conversion | `--convert-notebooks [PATH...]`; no paths means scan the repository notebooks |
| License | `--ensure-license bsd-3`, `mit`, or `ap2` |
| About section | `--about` |
| Directory-name translation | `--translate-dirs` |
| README translation | `--translate-readme LANG...` |
| Article-based README | `--attachment PATH_OR_URL` with `--readme` |
| Repository organization | `--organize` |

For docstring generation, `--ignore-list PATH...` excludes named directories/files; without it, OSA skips `__init__.py`. `--skip-health-check` disables the pre/post checks for repository organization and should be used only when requested.

Although `--refine-readme` appears in the argument configuration, the current execution path does not use it to select a different README operation. Do not present it as an available refinement stage.

Common repository selectors are `--repository URL`, `--branch NAME`, `--output PATH`, and `--based-on-date DATE`. The date option selects the closest repository revision and forces fork/PR creation off. `--artefacts-language LANG` controls generated report language.

## Repository and model options

- Use `--no-fork --no-pull-request` for a local-only run. With neither flag, the main CLI stars the remote repository and creates a fork before it clones the repository; if pull-request creation is also enabled, it later pushes a branch and opens a pull request.
- `--mode auto|basic|advanced` selects task planning behavior described above.
- `--api` currently accepts the providers listed in `osa_tool/config/settings/arguments.yaml`; use `--base-url` for a compatible endpoint and `--model` for a model choice.
- By default, task model profiles inherit the configured default. Use task-specific model flags when the user asks for different models by task. Use `--use-single-model` only when the user explicitly wants every task forced to the shared `[llm]` model; when set, it takes precedence over task-specific model profiles and overrides. Current task profiles include README, docstrings, general tasks, paper claims, paper verification, and repository quality.
- `--config-file TOML` selects a custom settings file. Avoid creating or editing one just to run a normal task.
- `--delete-dir` removes the repository directory after processing. For a remote URL, that is OSA's downloaded clone. For a local repository path without `--output`, OSA uses the supplied directory itself, so this flag can recursively delete the user's source checkout. Avoid it for local inputs; use it only for a remote clone when cleanup is explicitly requested.

Do not ask about temperature, top-p, token limit, or context window unless the request depends on them. The checked-in config owns those values. To see accepted options for this checkout, use `--help` rather than relying on the older README/FAQ flag tables.

## Workflow generation

Add `--generate-workflows` for CI workflow files. Documented controls include `--include-tests`, `--include-black`, `--include-pep8`, `--include-autopep8`, `--include-fix-pep8`, `--include-pypi`, `--include-ruff`, `--python-versions VERSIONS...`, `--pep8-tool flake8|pylint`, `--use-uv`, `--use-poetry`, `--branches BRANCHES...`, and `--include-codecov`.

The defaults already cover a common tests, Black, and PEP 8 setup. Add optional components only when asked. Avoid enabling both Black and Ruff formatting because their formatters can conflict. Verify every workflow flag with this checkout's `--help`; some options shown in workflow documentation may not be registered in the main CLI parser.

Relevant project documentation: `docs/scheduler/index.md`, `docs/workflow-generator/index.md`, `README.md` under Configuration, and `docs/faq/usage-features.md`.
