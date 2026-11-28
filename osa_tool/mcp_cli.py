"""Launcher for the optional OSA MCP server."""

import argparse
import os

_HOST = "127.0.0.1"


def main() -> None:
    """Serve the read-only MCP endpoint on IPv4 loopback."""
    parser = argparse.ArgumentParser(description="Serve OSA tools via Streamable HTTP on 127.0.0.1/mcp.")
    parser.add_argument("--port", type=int, default=8000, help="Loopback port (default: 8000)")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")

    try:
        from osa_tool.mcp_server import create_app
    except ModuleNotFoundError as exc:
        if exc.name != "mcp":
            raise
        parser.exit(1, 'OSA MCP support is not installed. Install it with: uv pip install "osa_tool[mcp]"\n')

    import uvicorn

    try:
        app = create_app(port=args.port, token=os.environ.get("OSA_MCP_TOKEN"))
    except ValueError as exc:
        parser.error(str(exc))
    uvicorn.run(
        app,
        host=_HOST,
        port=args.port,
        proxy_headers=False,
        access_log=False,
        limit_concurrency=32,
        timeout_graceful_shutdown=20,
    )
