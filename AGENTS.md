# Repository guidance

## Developer utilities

`osa_tool/tools/` is reserved for developer and research utilities. Its module commands are not supported entry points
for normal OSA usage.

- Do not inspect or modify files in `osa_tool/tools/` as part of ordinary user-facing feature work.
- Do not expose `python -m osa_tool.tools...` commands in the normal CLI reference, README, or user workflow examples.
- Use the supported `osa-tool` entry point for normal repository analysis.
- If a user-facing change appears to require editing `osa_tool/tools/`, explain that dependency and ask before entering
  that directory. An explicit request to work on a developer utility authorizes work on that utility.

The main CLI option metadata lives in `osa_tool/config/settings/arguments.yaml`. Generated CLI reference tables are
updated with `python docs/generate_cli_reference.py`.
