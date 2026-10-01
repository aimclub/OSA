from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

import dotenv

from osa_tool.config.settings import ModelSettings
from osa_tool.core.llm.llm import ModelHandler, _parse_llm_response
from osa_tool.utils.logger import logger
from osa_tool.utils.token_counter import count_tokens, truncate_to_tokens

DEFAULT_HOST_LLM_MODEL = "gpt-5.6-luna"


class HostLlmError(RuntimeError):
    """Raised when the subscription-backed host provider cannot complete a request."""

    def __init__(self, message: str, *, status: int = 0, provider_code: str = "host_llm_error"):
        super().__init__(message)
        self.status = status
        self.provider_code = provider_code
        self.provider_name = "Host LLM (subscription)"
        self.retry_after_ms = 0
        self.request_id = ""
        self.quota_metric = ""
        self.quota_description = ""
        self.network_code = ""


def normalize_host_model(model: str | None) -> str:
    value = (model or DEFAULT_HOST_LLM_MODEL).strip()
    if value.startswith("openai/"):
        value = value.removeprefix("openai/")
    return value or DEFAULT_HOST_LLM_MODEL


def host_command() -> str | None:
    configured = os.getenv("HOST_LLM_COMMAND", "").strip()
    return shutil.which(configured) if configured else None


def host_bridge_dir() -> Path | None:
    configured = os.getenv("HOST_LLM_BRIDGE_DIR", "").strip()
    return Path(configured).resolve() if configured else None


def host_provider_status(*, force: bool = False) -> dict[str, Any]:
    dotenv.load_dotenv(override=True)
    bridge_dir = host_bridge_dir()
    if bridge_dir:
        bridge_dir.mkdir(parents=True, exist_ok=True)
        return {
            "installed": True,
            "authenticated": True,
            "path": str(bridge_dir),
            "detail": "Host bridge is ready.",
            "transport": "host_bridge",
        }

    executable = host_command()
    if not executable:
        return {
            "installed": False,
            "authenticated": False,
            "path": None,
            "detail": "HOST_LLM_COMMAND is not set or is not available on PATH.",
        }

    try:
        completed = subprocess.run(
            [executable, "login", "status"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=10,
            check=False,
        )
        detail = (completed.stdout or "").strip()
        authenticated = completed.returncode == 0 and "not logged in" not in detail.lower()
        return {
            "installed": True,
            "authenticated": authenticated,
            "path": executable,
            "detail": detail or ("Login is active." if authenticated else "Login is not active."),
            "transport": "host_command",
        }
    except Exception as exc:  # pragma: no cover - environment dependent
        return {
            "installed": True,
            "authenticated": False,
            "path": executable,
            "detail": f"Could not inspect Host LLM status: {type(exc).__name__}: {exc}",
            "transport": "host_command",
        }


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _developer_instructions(system_prompt: str) -> str:
    return (
        "You are an LLM inference worker inside OSA. "
        "Do not inspect local files, run shell commands, browse, or ask follow-up questions. "
        "Use only the supplied user message. Follow these task instructions and answer directly.\n\n"
        f"{system_prompt.strip()}"
    )


def _user_prompt(user_message: str) -> str:
    return user_message.strip()


def _command(
    executable: str,
    model: str,
    output_path: Path,
    workspace: Path,
    developer_instructions: str,
) -> list[str]:
    return [
        executable,
        "exec",
        "--ephemeral",
        "--skip-git-repo-check",
        "--ignore-user-config",
        "-c",
        f"developer_instructions={_toml_string(developer_instructions)}",
        "--sandbox",
        "read-only",
        "--color",
        "never",
        "--model",
        normalize_host_model(model),
        "--cd",
        str(workspace),
        "--output-last-message",
        str(output_path),
        "-",
    ]


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("OPENAI_API_KEY", None)
    env.setdefault("NO_COLOR", "1")
    env.setdefault("FORCE_COLOR", "0")
    return env


def _run_host_bridge_sync(
    *,
    model: str,
    system_prompt: str,
    user_message: str,
    timeout_seconds: int,
) -> str:
    bridge_dir = host_bridge_dir()
    if bridge_dir is None:
        raise HostLlmError(
            "HOST_LLM_BRIDGE_DIR is not configured.",
            status=503,
            provider_code="host_bridge_not_configured",
        )

    requests_dir = bridge_dir / "requests"
    responses_dir = bridge_dir / "responses"
    requests_dir.mkdir(parents=True, exist_ok=True)
    responses_dir.mkdir(parents=True, exist_ok=True)
    request_id = f"osa-{uuid.uuid4().hex}"
    request_path = requests_dir / f"{request_id}.json"
    response_path = responses_dir / f"{request_id}.json"
    developer_instructions = _developer_instructions(system_prompt)
    safe_user_message = _user_prompt(user_message)
    request = {
        "request_id": request_id,
        "agent_name": "osa_host_llm_worker",
        "model": normalize_host_model(model),
        "developer_instructions": developer_instructions,
        "system_prompt": system_prompt.strip(),
        "user_message": safe_user_message,
        "prompt": safe_user_message,
        "messages": [
            {"role": "developer", "content": developer_instructions},
            {"role": "user", "content": safe_user_message},
        ],
        "response_path": str(response_path.resolve()),
        "created_at": time.time(),
    }
    temporary_path = requests_dir / f".{request_id}.tmp"
    temporary_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary_path, request_path)
    print(f"HOST_LLM_BRIDGE_REQUEST {request_path.resolve()}", flush=True)

    response = None
    last_json_error: BaseException | None = None
    started = time.monotonic()
    while response is None:
        if response_path.exists():
            try:
                response = json.loads(response_path.read_text(encoding="utf-8"))
                break
            except Exception as exc:
                last_json_error = exc
        if time.monotonic() - started > timeout_seconds:
            if last_json_error is not None:
                raise HostLlmError(
                    f"Host bridge response did not become valid JSON within {timeout_seconds} seconds: "
                    f"{last_json_error}",
                    status=502,
                    provider_code="host_bridge_invalid_response",
                ) from last_json_error
            raise HostLlmError(
                f"Host bridge did not return a response within {timeout_seconds} seconds.",
                status=504,
                provider_code="host_bridge_timeout",
            )
        time.sleep(0.25)

    if response.get("request_id") != request_id:
        raise HostLlmError(
            "Host bridge returned a response for a different request_id.",
            status=502,
            provider_code="host_bridge_id_mismatch",
        )
    if response.get("error"):
        raise HostLlmError(
            str(response["error"]),
            status=502,
            provider_code="host_bridge_worker_error",
        )
    requested_model = normalize_host_model(model)
    response_model = str(response.get("model") or requested_model)
    if response_model != requested_model:
        raise HostLlmError(
            f"Host bridge used {response_model} instead of {requested_model}.",
            status=502,
            provider_code="host_bridge_model_mismatch",
        )
    text = str(response.get("text") or "").strip()
    if not text:
        raise HostLlmError(
            "Host bridge returned an empty response.",
            status=502,
            provider_code="host_bridge_empty_response",
        )
    return text


def run_host_llm_sync(
    *,
    model: str,
    system_prompt: str,
    user_message: str,
    timeout_seconds: int | None = None,
) -> str:
    dotenv.load_dotenv(override=True)
    timeout = timeout_seconds or max(30, int(os.getenv("HOST_LLM_REQUEST_TIMEOUT_SECONDS", "600")))
    if host_bridge_dir():
        return _run_host_bridge_sync(
            model=model,
            system_prompt=system_prompt,
            user_message=user_message,
            timeout_seconds=timeout,
        )

    status = host_provider_status()
    if not status["installed"]:
        raise HostLlmError(str(status["detail"]), status=503, provider_code="host_unavailable")
    if not status["authenticated"]:
        raise HostLlmError(
            "Host LLM is not authenticated. Log in with the command configured in HOST_LLM_COMMAND.",
            status=401,
            provider_code="host_not_authenticated",
        )

    executable = str(status["path"])
    with tempfile.TemporaryDirectory(prefix="osa-host-") as raw_workspace:
        workspace = Path(raw_workspace)
        output_path = workspace / "last-message.txt"
        developer_instructions = _developer_instructions(system_prompt)
        safe_user_message = _user_prompt(user_message)
        try:
            completed = subprocess.run(
                _command(executable, model, output_path, workspace, developer_instructions),
                input=safe_user_message,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
                check=False,
                env=_clean_env(),
            )
        except subprocess.TimeoutExpired as exc:
            raise HostLlmError(
                f"Host LLM provider did not complete within {timeout} seconds.",
                status=504,
                provider_code="host_timeout",
            ) from exc

        raw = output_path.read_text(encoding="utf-8").strip() if output_path.exists() else ""
        if completed.returncode != 0:
            diagnostic = (completed.stderr or completed.stdout or "").strip()[-4000:]
            lowered = diagnostic.lower()
            status_code = 401 if "login" in lowered or "auth" in lowered else 502
            raise HostLlmError(
                f"Host LLM provider exited with code {completed.returncode}: "
                f"{diagnostic or 'no diagnostic output'}",
                status=status_code,
                provider_code="host_exec_failed",
            )
        if not raw:
            raw = (completed.stdout or "").strip()
        if not raw:
            raise HostLlmError(
                "Host LLM provider returned an empty response.",
                status=502,
                provider_code="host_empty_response",
            )
        return raw


async def run_host_llm(
    *,
    model: str,
    system_prompt: str,
    user_message: str,
    timeout_seconds: int | None = None,
) -> str:
    return await asyncio.to_thread(
        run_host_llm_sync,
        model=model,
        system_prompt=system_prompt,
        user_message=user_message,
        timeout_seconds=timeout_seconds,
    )


class HostLlmHandler(ModelHandler):
    """OSA ModelHandler backed by the user's subscription-aware host LLM."""

    def __init__(self, model_settings: ModelSettings):
        self.model_settings = model_settings
        self._original_primary_model = normalize_host_model(model_settings.model)
        self.max_retries = max(1, int(model_settings.max_retries))
        self.last_successful_model: str | None = None
        self.successful_models: list[str] = []
        dotenv.load_dotenv(override=True)

    def _system(self, system_message: str | None) -> str:
        return system_message or self.model_settings.system_prompt

    def _limit_tokens(
        self,
        text: str,
        safety_buffer: int = 100,
        mode: str = "middle-out",
        reserved_tokens: int = 0,
    ) -> str:
        max_input_tokens = (
            self.model_settings.context_window - self.model_settings.max_tokens - safety_buffer - reserved_tokens
        )
        if max_input_tokens <= 0:
            raise ValueError(
                "Invalid LLM token budget: context_window "
                f"({self.model_settings.context_window}) must exceed max_tokens "
                f"({self.model_settings.max_tokens}) + system tokens ({reserved_tokens}) "
                f"+ safety buffer ({safety_buffer}). Reduce max_tokens or increase context_window."
            )

        input_tokens = count_tokens(text, self.model_settings.encoder)
        if input_tokens <= max_input_tokens:
            return text

        logger.warning(
            "Host LLM user prompt exceeds the input budget and will be truncated: "
            "input_tokens=%s, available_input_tokens=%s, strategy=%s, model=%s",
            input_tokens,
            max_input_tokens,
            mode,
            self.model_settings.model,
        )
        return truncate_to_tokens(
            text,
            max_input_tokens,
            self.model_settings.encoder,
            mode=mode,
        )

    def _prepare_user_message(self, prompt: str, system_message: str | None) -> str:
        effective_system_message = self._system(system_message)
        developer_instructions = _developer_instructions(effective_system_message)
        system_tokens = count_tokens(developer_instructions, self.model_settings.encoder)
        original_user_tokens = count_tokens(prompt, self.model_settings.encoder)
        safe_prompt = self._limit_tokens(prompt, reserved_tokens=system_tokens)
        sent_user_tokens = count_tokens(safe_prompt, self.model_settings.encoder)
        logger.debug(
            "Host LLM token budget: model=%s, context_window=%s, max_output_tokens=%s, "
            "system_tokens=%s, user_tokens=%s, sent_user_tokens=%s, truncated=%s",
            self.model_settings.model,
            self.model_settings.context_window,
            self.model_settings.max_tokens,
            system_tokens,
            original_user_tokens,
            sent_user_tokens,
            sent_user_tokens < original_user_tokens,
        )
        return safe_prompt

    def _record_successful_model(self, model: str) -> None:
        normalized = normalize_host_model(model)
        self.last_successful_model = normalized
        if normalized not in self.successful_models:
            self.successful_models.append(normalized)

    def reset_model_provenance(self) -> None:
        self.last_successful_model = None
        self.successful_models.clear()

    def reset_to_primary_model(self) -> None:
        if normalize_host_model(self.model_settings.model) != self._original_primary_model:
            self.model_settings.model = self._original_primary_model

    def send_request(self, prompt: str, system_message: str = None, retry_delay: float = 1) -> str:
        model = self.model_settings.model
        safe_prompt = self._prepare_user_message(prompt, system_message)
        raw = run_host_llm_sync(
            model=model,
            system_prompt=self._system(system_message),
            user_message=safe_prompt,
        )
        self._record_successful_model(model)
        return raw

    async def async_request(self, prompt: str, system_message: str = None, retry_delay: float = 1) -> str:
        model = self.model_settings.model
        safe_prompt = self._prepare_user_message(prompt, system_message)
        raw = await run_host_llm(
            model=model,
            system_prompt=self._system(system_message),
            user_message=safe_prompt,
        )
        self._record_successful_model(model)
        return raw

    def send_and_parse(self, prompt: str, parser: Any, system_message: str = None, retry_delay: float = 0.5):
        last_error: BaseException | None = None
        last_raw: str | None = None
        for attempt in range(1, self.max_retries + 1):
            last_raw = self.send_request(prompt, system_message)
            try:
                return _parse_llm_response(last_raw, parser)
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(retry_delay)
        raise last_error

    async def async_send_and_parse(
        self,
        prompt: str,
        parser: Any,
        system_message: str = None,
        retry_delay: float = 0.5,
    ):
        last_error: BaseException | None = None
        for attempt in range(1, self.max_retries + 1):
            raw = await self.async_request(prompt, system_message)
            try:
                return _parse_llm_response(raw, parser)
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(retry_delay)
        raise last_error

    async def generate_concurrently(self, prompts: list[str], system_message: str = None) -> list[str]:
        return await asyncio.gather(*(self.async_request(prompt, system_message) for prompt in prompts))

    def run_chain(self, prompt: str, parser: Any, system_message: str = None, retry_delay: float = 0.5) -> Any:
        last_error: BaseException | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                raw = self.send_request(prompt, system_message)
                if hasattr(parser, "parse"):
                    return parser.parse(raw)
                return _parse_llm_response(raw, parser)
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(retry_delay)
        raise last_error

    async def async_run_chain(
        self,
        prompt: str,
        parser: Any,
        system_message: str = None,
        retry_delay: float = 0.5,
    ) -> Any:
        last_error: BaseException | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                raw = await self.async_request(prompt, system_message)
                if hasattr(parser, "parse"):
                    return parser.parse(raw)
                return _parse_llm_response(raw, parser)
            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    await asyncio.sleep(retry_delay)
        raise last_error
