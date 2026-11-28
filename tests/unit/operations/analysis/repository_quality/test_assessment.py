"""Test commit-pinned root metadata assessment without upstream network access."""

import asyncio
from collections.abc import AsyncIterator
from typing import TYPE_CHECKING, Any

import pytest

if TYPE_CHECKING:
    import httpx
else:
    httpx = pytest.importorskip("httpx")

from osa_tool.operations.analysis.repository_quality import assessment  # noqa: E402

assess_repository = assessment.assess_repository
pytestmark = pytest.mark.asyncio
_REPO_URL = "https://github.com/Example/Demo"
_REPO_GET = "/repos/Example/Demo"
_COMMIT_SHA = "a" * 40
_TREE_SHA = "b" * 40
_HEAD_GET = f"{_REPO_GET}/commits"
_COMMIT_GET = f"{_REPO_GET}/git/commits/{_COMMIT_SHA}"
_TREE_GET = f"{_REPO_GET}/git/trees/{_TREE_SHA}"
_CHECKS = ["readme", "license_file", "dependency_manifest"]


def _entry(path: str, mode: str = "100644", kind: str = "blob") -> dict[str, str]:
    return {"path": path, "mode": mode, "type": kind}


def _tree(*entries: object, truncated: bool = False) -> httpx.Response:
    return httpx.Response(200, json={"sha": _TREE_SHA, "tree": list(entries), "truncated": truncated})


class _GitHubStub:
    def __init__(self) -> None:
        tree = {"sha": _TREE_SHA}
        self.routes: dict[str, httpx.Response | Exception] = {
            _REPO_GET: httpx.Response(
                200, json={"full_name": "Example/Demo", "private": False}, headers={"Set-Cookie": "session=anonymous"}
            ),
            _HEAD_GET: httpx.Response(200, json=[{"sha": _COMMIT_SHA, "commit": {"tree": tree}}]),
            _COMMIT_GET: httpx.Response(200, json={"sha": _COMMIT_SHA, "tree": tree}),
            _TREE_GET: _tree(),
        }
        self.calls: list[str] = []

    def respond(self, request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.scheme == "https" and request.url.host == "api.github.com"
        assert dict(request.url.params) == ({"per_page": "1"} if request.url.path == _HEAD_GET else {})
        assert request.headers["accept-encoding"] == "identity"
        assert "authorization" not in request.headers and "cookie" not in request.headers
        self.calls.append(request.url.path)
        result = self.routes[request.url.path]
        if isinstance(result, Exception):
            raise result
        return result


@pytest.fixture
def github(monkeypatch: pytest.MonkeyPatch) -> _GitHubStub:
    stub = _GitHubStub()
    async_client = httpx.AsyncClient

    def client(**kwargs: Any) -> httpx.AsyncClient:
        assert kwargs["trust_env"] is False
        assert kwargs["follow_redirects"] is False
        assert kwargs["timeout"] > 0
        return async_client(transport=httpx.MockTransport(stub.respond), **kwargs)

    monkeypatch.setattr(assessment.httpx, "AsyncClient", client)
    return stub


@pytest.mark.parametrize("revision", [None, _COMMIT_SHA.upper()])
async def test_pins_evidence_to_resolved_commit(github: _GitHubStub, revision: str | None) -> None:
    """Resolve HEAD or a full SHA once; query only a nonrecursive tree and pin links."""
    github.routes["/repos/example/demo"] = github.routes[_REPO_GET]
    github.routes[_TREE_GET] = _tree(
        _entry("readme.md"), _entry("README"), _entry("NOTICE.é", "100755"), _entry("PyProject.TOML")
    )

    result = await assess_repository("HTTPS://GITHUB.COM/example/demo.git/", revision)

    commit_get = _HEAD_GET if revision is None else _COMMIT_GET
    assert github.calls == ["/repos/example/demo", commit_get, _TREE_GET]
    assert result.schema_version == "1"
    assert result.status == "ok"
    assert result.repository_url == _REPO_URL
    assert result.commit_sha == _COMMIT_SHA
    assert result.error_code is None
    assert [finding.check for finding in result.findings] == _CHECKS
    for finding, path, link_path in zip(
        result.findings, ["README", "NOTICE.é", "PyProject.TOML"], ["README", "NOTICE.%C3%A9", "PyProject.TOML"]
    ):
        assert finding.status == "present"
        assert finding.path == path
        assert finding.evidence_url == f"{_REPO_URL}/blob/{_COMMIT_SHA}/{link_path}"


async def test_complete_tree_excludes_nonfiles_and_inexact_names(github: _GitHubStub) -> None:
    """Directories, symlinks, submodules and inexact filenames don't count."""
    github.routes[_TREE_GET] = _tree(
        _entry("README", "040000", "tree"),
        _entry("LICENSE", "160000", "commit"),
        _entry("requirements.txt", "120000"),
        _entry("README.md.bak"),
        _entry("LICENSE.txt\n"),
        _entry("package.json"),
    )
    result = await assess_repository(_REPO_URL)
    assert result.status == "ok"
    assert result.error_code is None
    assert [finding.status for finding in result.findings] == ["absent"] * 3
    assert all(finding.path is None and finding.evidence_url is None for finding in result.findings)


@pytest.mark.parametrize("truncation", [{"truncated": True}, {}, {"truncated": 0}])
async def test_incomplete_tree_keeps_only_positive_evidence(github: _GitHubStub, truncation: dict[str, object]) -> None:
    """Only an explicit complete listing can establish absence."""
    github.routes[_TREE_GET] = httpx.Response(
        200, json={"sha": _TREE_SHA, "tree": [_entry("readme.RST")], **truncation}
    )
    result = await assess_repository(_REPO_URL)
    assert result.status == "partial"
    assert result.error_code == "incomplete_tree"
    assert result.commit_sha == _COMMIT_SHA
    readme, *unseen = result.findings
    assert readme.status == "present"
    assert readme.evidence_url == f"{_REPO_URL}/blob/{_COMMIT_SHA}/readme.RST"
    assert all(
        finding.status == "unknown" and finding.path is None and finding.evidence_url is None for finding in unseen
    )


async def test_malformed_entries_do_not_become_evidence(github: _GitHubStub) -> None:
    """Skip traversal paths, contradictory duplicate names, and malformed entries."""
    github.routes[_TREE_GET] = _tree(
        _entry("../README"),
        _entry("nested/LICENSE"),
        _entry("nested\\README"),
        _entry("README"),
        {"path": "README", "type": "blob"},
        {"path": "LICENSE", "type": "blob"},
        _entry("LICENSE"),
        _entry("requirements.txt"),
    )
    result = await assess_repository(_REPO_URL)
    assert result.status == "partial"
    assert [finding.status for finding in result.findings] == ["unknown", "unknown", "present"]
    assert all(finding.path is None and finding.evidence_url is None for finding in result.findings[:2])


@pytest.mark.parametrize(
    ("url", "revision", "error_code"),
    [
        ("http://github.com/Example/Demo", None, "invalid_url"),
        ("https://api.github.com/Example/Demo", None, "invalid_url"),
        ("https://github.com.bad.example/Example/Demo", None, "invalid_url"),
        ("https://username:secret@github.com/Example/Demo", None, "invalid_url"),
        ("https://github.com:443/Example/Demo", None, "invalid_url"),
        (_REPO_URL + "?token=secret", None, "invalid_url"),
        (_REPO_URL + "#secret", None, "invalid_url"),
        ("https://github.com/Example/..", None, "invalid_url"),
        ("https://github.com/Example/%2e%2e", None, "invalid_url"),
        ("https://github.com/Example/Demo\\secret", None, "invalid_url"),
        (_REPO_URL + "/../secret", None, "invalid_url"),
        (_REPO_URL + "\n", None, "invalid_url"),
        (_REPO_URL, "heads/main", "invalid_revision"),
        (_REPO_URL, "main", "invalid_revision"),
        (_REPO_URL, "a" * 39, "invalid_revision"),
        (_REPO_URL, "z" * 40, "invalid_revision"),
        (_REPO_URL, "a" * 40 + "\n", "invalid_revision"),
    ],
)
async def test_invalid_input_never_uses_network_or_echoes_input(
    github: _GitHubStub, url: str, revision: str | None, error_code: str
) -> None:
    """Reject ambiguous or sensitive URLs and non-SHA revisions before any I/O."""
    result = await assess_repository(url, revision)
    assert github.calls == []
    assert result.model_dump() == {
        "schema_version": "1",
        "status": "invalid_input",
        "repository_url": None,
        "commit_sha": None,
        "findings": [],
        "error_code": error_code,
    }


@pytest.mark.parametrize(
    ("route", "status", "headers", "error_code"),
    [
        (_REPO_GET, 404, {}, "not_accessible"),
        (_HEAD_GET, 404, {}, "not_accessible"),
        (_TREE_GET, 404, {}, "not_accessible"),
        (_TREE_GET, 500, {}, "github_error"),
        (_HEAD_GET, 403, {"x-ratelimit-remaining": "0"}, "rate_limited"),
        (_HEAD_GET, 403, {"retry-after": "10"}, "rate_limited"),
        (_HEAD_GET, 429, {}, "rate_limited"),
        (_REPO_GET, 301, {"location": "https://untrusted.example/secret"}, "github_error"),
    ],
)
async def test_http_failures_are_unknown_not_absent(
    github: _GitHubStub, route: str, status: int, headers: dict[str, str], error_code: str
) -> None:
    """Report upstream failures with no body passthrough, and never follow redirects."""
    github.routes[route] = httpx.Response(status, headers=headers, text="secret")
    result = await assess_repository(_REPO_URL)
    assert github.calls[-1] == route
    assert result.status == "unavailable"
    assert result.repository_url == _REPO_URL
    assert result.commit_sha == (_COMMIT_SHA if route == _TREE_GET else None)
    assert result.error_code == error_code
    assert [finding.check for finding in result.findings] == _CHECKS
    assert all(finding.status == "unknown" for finding in result.findings)
    assert all(finding.path is None and finding.evidence_url is None for finding in result.findings)
    assert "secret" not in result.model_dump_json()


@pytest.mark.parametrize(
    ("message", "error_code"),
    [
        ("You have exceeded a secondary rate limit. Private detail: secret", "rate_limited"),
        ("Resource not accessible. Private detail: secret", "not_accessible"),
    ],
)
async def test_forbidden_without_retry_headers_uses_bounded_error_body(
    github: _GitHubStub, message: str, error_code: str
) -> None:
    github.routes[_HEAD_GET] = httpx.Response(403, headers={"x-ratelimit-remaining": "10"}, json={"message": message})

    result = await assess_repository(_REPO_URL)

    assert result.status == "unavailable"
    assert result.error_code == error_code
    assert all(finding.status == "unknown" for finding in result.findings)
    assert "secret" not in result.model_dump_json()


@pytest.mark.parametrize(
    ("route", "payload", "error_code", "known_commit"),
    [
        (_REPO_GET, {"full_name": "different/repository", "private": False}, "invalid_response", False),
        (_REPO_GET, {"full_name": "Example/Demo", "private": True}, "not_accessible", False),
        (_REPO_GET, {"full_name": "Example/Demo", "private": False, "visibility": "internal"}, "not_accessible", False),
        (_HEAD_GET, [], "not_accessible", False),
        (_HEAD_GET, {}, "invalid_response", False),
        (_HEAD_GET, [{"sha": "../../bad", "commit": {"tree": {"sha": _TREE_SHA}}}], "invalid_response", False),
        (_HEAD_GET, [{"sha": _COMMIT_SHA, "commit": {"tree": {"sha": "../../bad"}}}], "invalid_response", True),
        (_TREE_GET, {"sha": "c" * 40, "tree": [_entry("README")], "truncated": False}, "invalid_response", True),
        (_TREE_GET, {"sha": _TREE_SHA, "tree": {}, "truncated": False}, "invalid_response", True),
    ],
)
async def test_unverified_metadata_produces_no_evidence(
    github: _GitHubStub, route: str, payload: object, error_code: str, known_commit: bool
) -> None:
    """Validate identity, visibility and SHAs before constructing further URLs."""
    github.routes[route] = httpx.Response(200, json=payload)
    result = await assess_repository(_REPO_URL)
    assert github.calls[-1] == route
    assert result.status == "unavailable"
    assert result.error_code == error_code
    assert result.commit_sha == (_COMMIT_SHA if known_commit else None)
    assert all(finding.status == "unknown" and finding.evidence_url is None for finding in result.findings)


async def test_requested_sha_must_match_resolved_sha(github: _GitHubStub) -> None:
    """A mismatching SHA isn't a resolved revision."""
    other_sha = "c" * 40
    endpoint = f"{_REPO_GET}/git/commits/{other_sha}"
    github.routes[endpoint] = github.routes[_COMMIT_GET]
    result = await assess_repository(_REPO_URL, other_sha)
    assert github.calls == [_REPO_GET, endpoint]
    assert result.status == "unavailable"
    assert result.error_code == "invalid_response"
    assert result.commit_sha is None


class _OversizedBody(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"x" * 256
        yield b"x" * 257
        pytest.fail("body must not be read once the byte cap is exceeded")


class _StalledBody(httpx.AsyncByteStream):
    async def __aiter__(self) -> AsyncIterator[bytes]:
        yield b"{"
        await asyncio.Event().wait()


async def test_streaming_size_limit_preserves_known_sha(github: _GitHubStub, monkeypatch: pytest.MonkeyPatch) -> None:
    """Bound actual bytes even if the response doesn't declare a length."""
    monkeypatch.setattr(assessment, "_MAX_RESPONSE_BYTES", 512)
    github.routes[_TREE_GET] = httpx.Response(200, stream=_OversizedBody())
    result = await assess_repository(_REPO_URL)
    assert result.status == "unavailable"
    assert result.error_code == "response_too_large"
    assert result.commit_sha == _COMMIT_SHA
    assert all(finding.status == "unknown" for finding in result.findings)


async def test_deadline_covers_response_stream(github: _GitHubStub, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop waiting for a streaming body at the total deadline."""
    monkeypatch.setattr(assessment, "_TOTAL_TIMEOUT_SECONDS", 0.02)
    github.routes[_TREE_GET] = httpx.Response(200, stream=_StalledBody())
    result = await asyncio.wait_for(assess_repository(_REPO_URL), timeout=1)
    assert result.status == "unavailable"
    assert result.error_code == "timeout"


@pytest.mark.parametrize(
    ("outcome", "error_code"),
    [
        (httpx.ReadTimeout("secret"), "timeout"),
        (httpx.ConnectError("secret"), "network_error"),
        (httpx.Response(200, text="secret is not JSON"), "invalid_response"),
        (httpx.Response(200, headers={"content-encoding": "gzip"}, stream=_OversizedBody()), "invalid_response"),
    ],
)
async def test_transport_and_body_failures_are_sanitized(
    github: _GitHubStub, outcome: httpx.Response | Exception, error_code: str
) -> None:
    """Do not emit raw transport errors or untrusted response data."""
    github.routes[_TREE_GET] = outcome
    result = await assess_repository(_REPO_URL)
    assert result.status == "unavailable"
    assert result.error_code == error_code
    assert result.commit_sha == _COMMIT_SHA
    assert "secret" not in result.model_dump_json()
