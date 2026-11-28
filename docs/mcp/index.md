# MCP repository assessment

`osa-mcp` serves one read-only tool, `assess_repository`. It checks the root of a public GitHub repository for a README, a license marker, and a Python dependency manifest (`requirements.txt` or `pyproject.toml`). It does not clone repositories, run an LLM, or publish changes.

## Start the server

From a source checkout with [uv](https://docs.astral.sh/uv/):

```sh
uv venv --python 3.11
uv pip install -e ".[mcp]"
uv run --no-project osa-mcp
```

Connect a Streamable HTTP MCP client to `http://127.0.0.1:8000/mcp`. Use `osa-mcp --port 8010` to change the port.
This server binds to IPv4 loopback only and checks the HTTP Host and Origin headers. Leave it on a trusted machine;
this version is not intended for remote access or reverse-proxy deployment.

Authentication is off unless you set `OSA_MCP_TOKEN` in the server process environment. On shared machines, set
it to a strong random token and configure the client to send `Authorization: Bearer <token>`. Supply the token
through your environment or secret manager, not in a URL or command-line argument. This token guards the local MCP
endpoint; it is not a GitHub credential.

## Call the tool

Pass `repository_url` as `https://github.com/OWNER/REPO`. Pass `revision` as a full 40-character commit SHA, or omit it to check the default branch's HEAD. Branch names, tags, and short SHAs return `invalid_input`.

```json
{"repository_url": "https://github.com/example/demo", "revision": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"}
```

The following are illustrative `structuredContent` results, not live checks. A successful assessment links to the
file at the resolved commit. `absent` means the check completed and did not find a matching root file.

```json
{
  "schema_version": "1",
  "status": "ok",
  "repository_url": "https://github.com/example/demo",
  "commit_sha": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "findings": [
    {
      "check": "readme",
      "status": "present",
      "path": "README.md",
      "evidence_url": "https://github.com/example/demo/blob/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/README.md"
    },
    {"check": "license_file", "status": "absent", "path": null, "evidence_url": null},
    {"check": "dependency_manifest", "status": "absent", "path": null, "evidence_url": null}
  ],
  "error_code": null
}
```

If GitHub reports the repository or revision is inaccessible before a commit can be resolved, the checks are
`unknown`, not `absent`. Consumers should inspect `status` and `error_code`: this is a typed tool result, not
an MCP protocol error.

```json
{
  "schema_version": "1",
  "status": "unavailable",
  "repository_url": "https://github.com/example/demo",
  "commit_sha": null,
  "findings": [
    {"check": "readme", "status": "unknown", "path": null, "evidence_url": null},
    {"check": "license_file", "status": "unknown", "path": null, "evidence_url": null},
    {"check": "dependency_manifest", "status": "unknown", "path": null, "evidence_url": null}
  ],
  "error_code": "not_accessible"
}
```

Other statuses are `partial` (some checks remain `unknown`) and `invalid_input`. The checks report file presence,
not the quality of the README, the validity of the license, or the installability of dependencies.

## Test locally

In the same virtual environment, install the test dependencies and run the opt-in transport tests:

```sh
uv pip install "pytest>=8.3" "pytest-asyncio>=1.0"
uv run --no-project pytest --noconftest -m mcp tests/integration/test_mcp_http.py
```

The tests start a server on an ephemeral loopback port and use the MCP Python SDK to discover and call the tool. They use simulated GitHub responses and need neither GitHub access nor an LLM credential.
