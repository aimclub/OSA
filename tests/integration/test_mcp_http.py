"""Exercise the real Streamable HTTP endpoint with the MCP SDK and no upstream network."""

import asyncio
import socket
import sys
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock

import pytest

pytestmark = [pytest.mark.mcp, pytest.mark.asyncio]
pytest.importorskip("mcp")

import httpx
import uvicorn
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from osa_tool import mcp_cli, mcp_server
from osa_tool.operations.analysis.repository_quality import assessment
from osa_tool.operations.analysis.repository_quality.assessment import RepositoryAssessment

_REPOSITORY_URL = "https://github.com/example/demo"
_COMMIT = "a" * 40
_CHECKS = ("readme", "license_file", "dependency_manifest")


@asynccontextmanager
async def _serve(*, token: str | None = None) -> AsyncIterator[str]:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        port = listener.getsockname()[1]
        server = uvicorn.Server(
            uvicorn.Config(mcp_server.create_app(port=port, token=token), lifespan="on", access_log=False)
        )
        task = asyncio.create_task(server.serve(sockets=[listener]))
        try:
            async with asyncio.timeout(5):
                while not server.started:
                    if task.done():
                        await task
                        raise RuntimeError("MCP server exited before starting")
                    await asyncio.sleep(0.01)
            yield f"http://127.0.0.1:{port}/mcp"
        finally:
            server.should_exit = True
            await asyncio.wait_for(task, timeout=5)


def _assessment(*, available: bool) -> RepositoryAssessment:
    return RepositoryAssessment.model_validate(
        {
            "schema_version": "1",
            "status": "ok" if available else "unavailable",
            "repository_url": _REPOSITORY_URL,
            "commit_sha": _COMMIT if available else None,
            "findings": [
                {
                    "check": check,
                    "status": ("present" if check == "readme" else "absent") if available else "unknown",
                    "path": "README.md" if available and check == "readme" else None,
                    "evidence_url": (
                        f"{_REPOSITORY_URL}/blob/{_COMMIT}/README.md" if available and check == "readme" else None
                    ),
                }
                for check in _CHECKS
            ],
            "error_code": None if available else "not_accessible",
        }
    )


async def test_assessment_on_streamable_http(monkeypatch: pytest.MonkeyPatch) -> None:
    """Initialize, discover, and call the public tool over TCP; preserve typed failures."""
    expected = [_assessment(available=True), _assessment(available=False)]
    secret = "secret-from-upstream"
    operation = AsyncMock(side_effect=[*expected, RuntimeError(secret)])

    async with _serve() as url, httpx.AsyncClient(trust_env=False, timeout=5) as client:
        async with streamable_http_client(url, http_client=client) as (read, write, session_id):
            async with ClientSession(read, write) as session:
                await session.initialize()
                assert session_id() is None
                (tool,) = (await session.list_tools()).tools
                assert tool.name == "assess_repository"
                assert tool.annotations and tool.annotations.readOnlyHint is True
                assert tool.inputSchema["required"] == ["repository_url"]
                assert "40-character commit SHA" in tool.inputSchema["properties"]["revision"]["description"]
                assert tool.outputSchema and "findings" in tool.outputSchema["properties"]

                invalid = await session.call_tool(tool.name, {"repository_url": _REPOSITORY_URL, "revision": "main"})
                assert not invalid.isError
                assert invalid.structuredContent == RepositoryAssessment(
                    status="invalid_input", error_code="invalid_revision"
                ).model_dump(mode="json")

                monkeypatch.setattr(mcp_server, "_assess_repository", operation)
                for expected_assessment in expected:
                    result = await session.call_tool(
                        tool.name, {"repository_url": _REPOSITORY_URL, "revision": _COMMIT}
                    )
                    assert not result.isError
                    assert result.structuredContent == expected_assessment.model_dump(mode="json")

                result = await session.call_tool(tool.name, {"repository_url": _REPOSITORY_URL})
                assert result.isError
                assert result.structuredContent is None
                assert "Repository assessment failed." in str(result.content)
                assert secret not in result.model_dump_json()
    operation.assert_any_await(_REPOSITORY_URL, revision=_COMMIT)
    operation.assert_awaited_with(_REPOSITORY_URL, revision=None)


async def test_commit_evidence_from_github_metadata_over_mcp(monkeypatch: pytest.MonkeyPatch) -> None:
    tree_sha = "b" * 40
    root = "/repos/example/demo"
    replies = {
        root: {"full_name": "example/demo", "private": False},
        f"{root}/git/commits/{_COMMIT}": {"sha": _COMMIT, "tree": {"sha": tree_sha}},
        f"{root}/git/trees/{tree_sha}": {
            "sha": tree_sha,
            "truncated": False,
            "tree": [{"type": "blob", "mode": "100644", "path": "README.md"}],
        },
    }
    calls = []

    def github(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        return httpx.Response(200, json=replies[request.url.path])

    def github_client() -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url="https://api.github.com", transport=httpx.MockTransport(github))

    monkeypatch.setattr(assessment, "_github_client", github_client)
    async with _serve() as url, httpx.AsyncClient(trust_env=False, timeout=5) as client:
        async with streamable_http_client(url, http_client=client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(
                    "assess_repository", {"repository_url": _REPOSITORY_URL, "revision": _COMMIT}
                )

    assert calls == list(replies)
    assert not result.isError
    assert result.structuredContent == _assessment(available=True).model_dump(mode="json")


async def test_launcher_bounds_graceful_shutdown(monkeypatch: pytest.MonkeyPatch) -> None:
    run = Mock()
    monkeypatch.delenv("OSA_MCP_TOKEN", raising=False)
    monkeypatch.setattr(sys, "argv", ["osa-mcp", "--port", "8010"])
    monkeypatch.setattr(uvicorn, "run", run)

    mcp_cli.main()

    assert run.call_args.kwargs["host"] == "127.0.0.1"
    assert run.call_args.kwargs["timeout_graceful_shutdown"] == 20


async def test_http_bearer_auth_and_rebinding_protection() -> None:
    """Reject unauthenticated requests and off-origin or off-host requests before running tools."""
    token = "mcp-integration-test-token"
    async with _serve(token=token) as url, httpx.AsyncClient(trust_env=False, timeout=5) as client:
        for headers in ({}, {"Authorization": "Bearer incorrect"}):
            response = await client.get(url, headers=headers)
            assert response.status_code == 401
            assert response.headers["WWW-Authenticate"] == "Bearer"
            assert token not in response.text

        client.headers["Authorization"] = f"Bearer {token}"
        assert (await client.get(url, headers={"Host": "example.net"})).status_code == 421
        assert (await client.get(url, headers={"Origin": "https://example.net"})).status_code == 403
        async with streamable_http_client(url, http_client=client) as (read, write, _):
            async with ClientSession(read, write) as session:
                await session.initialize()
                assert [tool.name for tool in (await session.list_tools()).tools] == ["assess_repository"]
