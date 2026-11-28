"""Optional Streamable HTTP adapter for the repository assessment operation."""

import re
from asyncio import BoundedSemaphore
from secrets import compare_digest
from typing import Annotated

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.exceptions import ToolError
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import ToolAnnotations
from pydantic import Field
from starlette.applications import Starlette
from starlette.datastructures import Headers
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Receive, Scope, Send

from osa_tool.operations.analysis.repository_quality.assessment import RepositoryAssessment
from osa_tool.operations.analysis.repository_quality.assessment import assess_repository as _assess_repository

_HOST = "127.0.0.1"
_MAX_ASSESSMENTS = 4


class _BearerAuth:
    def __init__(self, app: ASGIApp, token: str) -> None:
        self.app = app
        self._expected_token = token.encode("ascii")

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http":
            headers = Headers(scope=scope).getlist("authorization")
            # Check the header only; the shared token has no OAuth issuer and is never sent upstream.
            scheme, _, token = headers[0].partition(" ") if len(headers) == 1 else ("", "", "")
            if scheme.lower() != "bearer" or not compare_digest(token.encode("latin-1"), self._expected_token):
                response = JSONResponse(
                    {"error": "unauthorized"}, status_code=401, headers={"WWW-Authenticate": "Bearer"}
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def create_app(*, port: int, token: str | None = None) -> Starlette:
    """Build the single-tool stateless HTTP app.

    Args:
        port: Loopback listener port to allow in Host and Origin headers.
        token: Static bearer credential, or None for loopback-only unauthenticated access.
    """
    if token is not None and not re.fullmatch(r"[A-Za-z0-9._~+/-]+=*", token):
        raise ValueError("OSA_MCP_TOKEN must be a non-empty bearer token without whitespace.")
    authority = f"{_HOST}:{port}"
    server = FastMCP(
        "OSA",
        host=_HOST,
        port=port,
        streamable_http_path="/mcp",
        stateless_http=True,
        json_response=True,
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=True,
            allowed_hosts=[_HOST, authority],
            allowed_origins=[f"http://{authority}"],
        ),
    )
    limiter = BoundedSemaphore(_MAX_ASSESSMENTS)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=True), structured_output=True)
    async def assess_repository(
        repository_url: Annotated[str, Field(description="HTTPS URL of a public GitHub repository.")],
        revision: Annotated[
            str | None, Field(description="Full 40-character commit SHA; omit for default HEAD.")
        ] = None,
    ) -> RepositoryAssessment:
        """Check for a root README, license marker, and Python dependency manifest."""
        if limiter.locked():
            raise ToolError("Repository assessment capacity reached; retry later.")
        async with limiter:
            try:
                return await _assess_repository(repository_url, revision=revision)
            except Exception:
                raise ToolError("Repository assessment failed.") from None

    app = server.streamable_http_app()
    if token is not None:
        app.add_middleware(_BearerAuth, token=token)
    return app
