"""Assess root file presence from public GitHub metadata without reading file contents."""

import asyncio
import json
import re
from typing import Literal
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field

from ._root_files import ROOT_FILE_CHECKS, RootFileCheck, find_root_file

_WEB_BASE = "https://github.com"
_API_BASE = "https://api.github.com"
_REPOSITORY_URL = re.compile(r"(?i:https://github\.com)/([A-Za-z0-9-]{1,39}/[A-Za-z0-9_.-]{1,104})/?")
_FULL_NAME = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?/[A-Za-z0-9_.-]{1,100}")
_SHA = re.compile(r"[0-9a-fA-F]{40}")
_MAX_RESPONSE_BYTES = 8 * 1024 * 1024
_MAX_ERROR_BYTES = 8 * 1024
_TOTAL_TIMEOUT_SECONDS = 15.0
_HTTP_TIMEOUT_SECONDS = 5.0
_REGULAR_MODES = frozenset({("blob", "100644"), ("blob", "100755")})
_OTHER_MODES = frozenset({("blob", "120000"), ("tree", "040000"), ("commit", "160000")})

AssessmentError = Literal[
    "invalid_url",
    "invalid_revision",
    "not_accessible",
    "rate_limited",
    "timeout",
    "network_error",
    "github_error",
    "invalid_response",
    "response_too_large",
    "incomplete_tree",
]


class RepositoryFinding(BaseModel):
    """Presence of an ordinary root file and its commit-pinned evidence, if found."""

    check: RootFileCheck
    status: Literal["present", "absent", "unknown"]
    path: str | None = None
    evidence_url: str | None = None


class RepositoryAssessment(BaseModel):
    """Versioned results of a metadata-only public repository assessment."""

    schema_version: Literal["1"] = "1"
    status: Literal["ok", "partial", "unavailable", "invalid_input"]
    repository_url: str | None = None
    commit_sha: str | None = None
    findings: list[RepositoryFinding] = Field(default_factory=list)
    error_code: AssessmentError | None = None


class _GitHubError(Exception):
    def __init__(self, code: AssessmentError) -> None:
        super().__init__(code)
        self.code = code


def _valid_full_name(value: object) -> bool:
    return isinstance(value, str) and bool(_FULL_NAME.fullmatch(value)) and value.split("/")[1] not in {".", ".."}


def _normalize_url(url: str) -> str | None:
    match = _REPOSITORY_URL.fullmatch(url)
    if not match:
        return None
    full_name = match[1]
    if full_name.lower().endswith(".git"):
        full_name = full_name[:-4]
    return full_name if _valid_full_name(full_name) else None


async def _read_json(response: httpx.Response, max_bytes: int) -> object:
    # Reject compressed bodies so the cap also bounds decompressed bytes.
    if response.headers.get("content-encoding", "identity").lower() != "identity":
        raise _GitHubError("invalid_response")
    body = bytearray()
    async for chunk in response.aiter_bytes():
        if len(body) + len(chunk) > max_bytes:
            raise _GitHubError("response_too_large")
        body.extend(chunk)
    try:
        return json.loads(body)
    except (ValueError, RecursionError) as exc:
        raise _GitHubError("invalid_response") from exc


async def _status_error(response: httpx.Response) -> AssessmentError:
    status = response.status_code
    if status == 429:
        return "rate_limited"
    if status == 403:
        if response.headers.get("x-ratelimit-remaining") == "0" or "retry-after" in response.headers:
            return "rate_limited"
        try:
            payload = await _read_json(response, _MAX_ERROR_BYTES)
        except (_GitHubError, httpx.RequestError):
            return "not_accessible"
        message = payload.get("message") if isinstance(payload, dict) else None
        if isinstance(message, str) and "secondary rate limit" in message.casefold():
            return "rate_limited"
    if status in (401, 403, 404):
        return "not_accessible"
    return "github_error"


async def _get_json(client: httpx.AsyncClient, path: str, *, params: dict[str, int] | None = None) -> object:
    client.cookies.clear()  # Each GitHub request is anonymous, even after a Set-Cookie.
    async with client.stream("GET", path, params=params) as response:
        if response.status_code != 200:
            raise _GitHubError(await _status_error(response))
        return await _read_json(response, _MAX_RESPONSE_BYTES)


def _as_object(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        raise _GitHubError("invalid_response")
    return payload


def _public_name(payload: dict[str, object], requested_name: str) -> str:
    if payload.get("private") is True or payload.get("visibility", "public") != "public":
        raise _GitHubError("not_accessible")
    full_name = payload.get("full_name")
    if (
        payload.get("private") is not False
        or not isinstance(full_name, str)
        or not _valid_full_name(full_name)
        or full_name.lower() != requested_name.lower()
    ):
        raise _GitHubError("invalid_response")
    return full_name


def _object_sha(payload: object) -> str:
    sha = payload.get("sha") if isinstance(payload, dict) else None
    if not isinstance(sha, str) or not _SHA.fullmatch(sha):
        raise _GitHubError("invalid_response")
    return sha.lower()


async def _get_commit(client: httpx.AsyncClient, api_path: str, revision: str | None) -> dict[str, object]:
    # List commits on the default branch or use the Git database endpoint; neither includes patches.
    if revision is not None:
        return _as_object(await _get_json(client, f"{api_path}/git/commits/{revision}"))
    commits = await _get_json(client, f"{api_path}/commits", params={"per_page": 1})
    if commits == []:
        raise _GitHubError("not_accessible")
    if not isinstance(commits, list) or len(commits) != 1:
        raise _GitHubError("invalid_response")
    return _as_object(commits[0])


def _tree_files(payload: dict[str, object], tree_sha: str) -> tuple[list[str], bool]:
    entries = payload.get("tree")
    if _object_sha(payload) != tree_sha or not isinstance(entries, list):
        raise _GitHubError("invalid_response")
    complete = payload.get("truncated") is False
    seen: set[str] = set()
    files: set[str] = set()
    for entry in entries:
        path = entry.get("path") if isinstance(entry, dict) else None
        if not isinstance(path, str) or not path or path in (".", "..") or any(c in path for c in ("/", "\\", "\0")):
            complete = False
            continue
        if path in seen:
            files.discard(path)
            complete = False
            continue
        seen.add(path)
        match entry:
            case {"type": str() as kind, "mode": str() as mode} if (kind, mode) in _REGULAR_MODES:
                files.add(path)
            case {"type": str() as kind, "mode": str() as mode} if (kind, mode) in _OTHER_MODES:
                pass
            case _:
                complete = False
    return sorted(files), complete


def _findings(paths: list[str], complete: bool, evidence_base: str | None = None) -> list[RepositoryFinding]:
    findings: list[RepositoryFinding] = []
    for check in ROOT_FILE_CHECKS:
        path = find_root_file(paths, check)
        if path is None:
            findings.append(RepositoryFinding(check=check, status="absent" if complete else "unknown"))
        else:
            evidence_url = f"{evidence_base}/{quote(path, safe='')}" if evidence_base is not None else None
            findings.append(RepositoryFinding(check=check, status="present", path=path, evidence_url=evidence_url))
    return findings


def _github_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url=_API_BASE,
        follow_redirects=False,
        trust_env=False,
        timeout=_HTTP_TIMEOUT_SECONDS,
        headers={
            "Accept": "application/vnd.github+json",
            "Accept-Encoding": "identity",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )


async def _assess(full_name: str, revision: str | None) -> RepositoryAssessment:
    commit_sha: str | None = None
    error_code: AssessmentError
    try:
        async with asyncio.timeout(_TOTAL_TIMEOUT_SECONDS), _github_client() as client:
            metadata = _as_object(await _get_json(client, f"/repos/{full_name}"))
            full_name = _public_name(metadata, full_name)
            api_path = f"/repos/{full_name}"
            commit = await _get_commit(client, api_path, revision)
            resolved_sha = _object_sha(commit)
            if revision is not None and resolved_sha != revision:
                raise _GitHubError("invalid_response")
            commit_sha = resolved_sha
            commit_data = _as_object(commit.get("commit")) if revision is None else commit
            tree_sha = _object_sha(commit_data.get("tree"))
            tree = _as_object(await _get_json(client, f"{api_path}/git/trees/{tree_sha}"))
            paths, complete = _tree_files(tree, tree_sha)
            return _tree_assessment(full_name, resolved_sha, paths, complete)
    except _GitHubError as exc:
        error_code = exc.code
    except (TimeoutError, httpx.TimeoutException):
        error_code = "timeout"
    except httpx.RequestError:
        error_code = "network_error"
    return RepositoryAssessment(
        status="unavailable",
        repository_url=f"{_WEB_BASE}/{full_name}",
        commit_sha=commit_sha,
        findings=_findings([], complete=False),
        error_code=error_code,
    )


def _tree_assessment(full_name: str, commit_sha: str, paths: list[str], complete: bool) -> RepositoryAssessment:
    repository_url = f"{_WEB_BASE}/{full_name}"
    return RepositoryAssessment(
        status="ok" if complete else "partial",
        repository_url=repository_url,
        commit_sha=commit_sha,
        findings=_findings(paths, complete, f"{repository_url}/blob/{commit_sha}"),
        error_code=None if complete else "incomplete_tree",
    )


async def assess_repository(repository_url: str, revision: str | None = None) -> RepositoryAssessment:
    """Check whether a public GitHub repository has a few common root files.

    Args:
        repository_url: An HTTPS GitHub repository URL, optionally ending in `.git` or `/`.
        revision: A full commit SHA, or None to resolve the default branch's HEAD.

    Returns:
        A commit-pinned assessment, or a sanitized result when input or metadata is unavailable.
    """
    full_name = _normalize_url(repository_url)
    if full_name is None:
        return RepositoryAssessment(status="invalid_input", error_code="invalid_url")
    if revision is not None and not _SHA.fullmatch(revision):
        return RepositoryAssessment(status="invalid_input", error_code="invalid_revision")
    return await _assess(full_name, revision.lower() if revision is not None else None)
