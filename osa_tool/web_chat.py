"""JSON-lines transport for the agent graph used by browser clients.

The terminal chat remains in :mod:`osa_tool.run_chat`. Only this opt-in mode
uses stdin and stdout as a machine-readable protocol.
"""

from __future__ import annotations

import json
import os
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, TextIO

from osa_tool.config.osa_config import OSAConfig
from osa_tool.config.settings import ConfigManager
from osa_tool.core.models.agent_status import AgentStatus
from osa_tool.osa_agent.context import AgentContext
from osa_tool.osa_agent.graph import build_graph
from osa_tool.osa_agent.state import OSAState
from osa_tool.run import initialize_git_platform, resolve_publishing_options
from osa_tool.ui.input_for_chat import _web_question_handler
from osa_tool.utils.logger import logger, setup_logging
from osa_tool.utils.utils import (
    osa_project_root,
    parse_folder_name,
    prepare_local_output_repository,
    switch_to_output_directory,
)


class ChatProtocolError(ValueError):
    """The browser sent an invalid protocol message."""


class ChatCancelled(Exception):
    """The browser closed or cancelled an interactive run."""


class JsonLineChatIO:
    def __init__(self, source: TextIO, sink: TextIO):
        self.source = source
        self.sink = sink
        self.output_dir: Path | None = None

    def emit(self, event_type: str, **fields: Any) -> None:
        self.sink.write(json.dumps({"type": event_type, **fields}, default=str) + "\n")
        self.sink.flush()

    def _read(self) -> dict[str, Any]:
        line = self.source.readline(1_048_577)
        if not line:
            raise ChatCancelled("Browser connection closed")
        if len(line) > 1_048_576:
            raise ChatProtocolError("Message is too large")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ChatProtocolError("Expected a JSON object") from exc
        if not isinstance(value, dict):
            raise ChatProtocolError("Expected a JSON object")
        if value.get("type") == "cancel":
            raise ChatCancelled("Run cancelled")
        return value

    def read_start(self) -> dict[str, str | None]:
        message = self._read()
        repository = message.get("repository")
        request = message.get("request")
        attachment = message.get("attachment")
        if message.get("type") != "start":
            raise ChatProtocolError("First message must have type 'start'")
        if not isinstance(repository, str) or not repository.strip():
            raise ChatProtocolError("Repository is required")
        if not isinstance(request, str) or not request.strip():
            raise ChatProtocolError("Request is required")
        if attachment is not None and not isinstance(attachment, str):
            raise ChatProtocolError("Attachment must be a string or null")
        return {
            "repository": repository.strip(),
            "request": request.strip(),
            "attachment": attachment.strip() or None if isinstance(attachment, str) else None,
        }

    def ask(self, state: OSAState) -> dict[str, str | None]:
        payload = state.clarification_payload or {}
        fields = payload.get("fields", [])
        question_id = uuid.uuid4().hex
        if state.clarification_type == "review":
            self.emit(
                "review",
                tasks=_task_results(state),
                artifacts=_artifact_paths(state, self.output_dir),
                events=_artifact_events(state),
            )
        self.emit(
            "question",
            id=question_id,
            agent=state.clarification_agent,
            kind=state.clarification_type,
            question=payload.get("question", "Additional information required"),
            fields=fields,
        )
        while True:
            try:
                message = self._read()
                if message.get("type") != "answer" or message.get("id") != question_id:
                    raise ChatProtocolError("Answer does not match the pending question")
                values = message.get("values")
                if not isinstance(values, dict):
                    raise ChatProtocolError("Answer values must be an object")
                names = {field["name"] for field in fields}
                if set(values) - names:
                    raise ChatProtocolError("Answer contains unknown fields")
                answers: dict[str, str | None] = {}
                for field in fields:
                    name = field["name"]
                    value = values.get(name)
                    if value is not None and not isinstance(value, str):
                        raise ChatProtocolError(f"{name} must be text")
                    value = value.strip() if value else None
                    if field.get("required") and not value:
                        raise ChatProtocolError(f"{name} is required")
                    if name == "accept" and value and value.lower() not in {"yes", "y", "no", "n"}:
                        raise ChatProtocolError("Approval must be yes or no")
                    answers[name] = value
                return answers
            except ChatProtocolError as exc:
                self.emit("error", message=str(exc), recoverable=True)


@contextmanager
def use_web_questions(handler):
    token = _web_question_handler.set(handler)
    try:
        yield
    finally:
        _web_question_handler.reset(token)


def _artifact_paths(state: OSAState, output_dir: Path | None) -> list[str]:
    if output_dir is None:
        return []
    paths: set[str] = set()
    for artifact in state.artifacts.values():
        if not isinstance(artifact, dict):
            continue
        for event in artifact.get("events", []):
            target = event.get("target") if isinstance(event, dict) else getattr(event, "target", None)
            if not isinstance(target, (str, Path)):
                continue
            path = Path(target)
            if not path.is_absolute():
                path = Path(state.repo_path or output_dir) / path
            path = path.resolve()
            if path.is_file() and path.is_relative_to(output_dir):
                paths.add(str(path))
    return sorted(paths)


def _task_results(state: OSAState) -> list[dict[str, Any]]:
    return [{"id": task.id, "status": task.status.value, "result": task.result} for task in state.plan]


def _artifact_events(state: OSAState) -> list[dict[str, str]]:
    events: list[dict[str, str]] = []
    for artifact in state.artifacts.values():
        if not isinstance(artifact, dict):
            continue
        for event in artifact.get("events", []):
            kind = event.get("kind") if isinstance(event, dict) else getattr(event, "kind", None)
            target = event.get("target") if isinstance(event, dict) else getattr(event, "target", None)
            if kind is not None and target is not None:
                events.append({"kind": str(getattr(kind, "value", kind)), "target": str(target)})
    return events[:50]


def _run(args, io: JsonLineChatIO) -> int:
    start = io.read_start()
    args.repository = start["repository"]
    output_dir = Path(args.output).resolve() if args.output else None
    io.output_dir = output_dir
    logs_dir = args.log_dir or str(Path(osa_project_root()).parent / "logs")
    setup_logging(parse_folder_name(args.repository), logs_dir)

    if output_dir is not None:
        switch_to_output_directory(output_dir)
        if os.path.isdir(args.repository):
            args.repository = str(prepare_local_output_repository(args.repository, output_dir))

    config_manager = ConfigManager(args)
    git_agent, workflow_manager = initialize_git_platform(args, config_manager)
    create_fork, create_pull_request = resolve_publishing_options(args, git_agent)
    context = AgentContext(
        OSAConfig(
            config_manager=config_manager,
            git_agent=git_agent,
            workflow_manager=workflow_manager,
            create_fork=create_fork,
            create_pull_request=create_pull_request,
            delete_dir=args.delete_dir,
            enable_replanning=True,
            enable_memory=True,
        )
    )
    state = OSAState(
        repo_url=start["repository"],
        attachment=start["attachment"],
        active_request=start["request"],
        active_request_source="user",
        session_id=uuid.uuid4().hex,
        status=AgentStatus.INIT,
    )
    io.emit("started", session_id=state.session_id)
    with use_web_questions(io.ask):
        for value in build_graph(context).stream(state, stream_mode="values"):
            state = OSAState.model_validate(value)
            if state.active_agent:
                io.emit("progress", agent=state.active_agent, status=state.status.value)

    if state.review_cycles_exhausted:
        io.emit("stopped", reason="review_cycles_exhausted", message="Revision limit reached without approval")
        return 0
    if state.status != AgentStatus.COMPLETED:
        raise RuntimeError(f"Agent graph ended with status {state.status.value}")
    io.emit(
        "completed",
        summary=state.final_summary or "Run completed",
        tasks=_task_results(state),
        artifacts=_artifact_paths(state, output_dir),
        pull_request_url=state.pull_request_url,
    )
    return 0


def run_web_chat(args) -> int:
    """Run the web protocol with stdout reserved exclusively for JSON lines."""
    sys.stdout.flush()
    wire = os.fdopen(os.dup(sys.stdout.fileno()), "w", encoding="utf-8", buffering=1)
    os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
    sys.stdout = sys.stderr
    io = JsonLineChatIO(sys.stdin, wire)
    try:
        return _run(args, io)
    except ChatCancelled as exc:
        io.emit("stopped", reason="cancelled", message=str(exc))
        return 0
    except Exception as exc:
        logger.exception("Web chat failed")
        io.emit("error", message=str(exc), recoverable=False)
        return 1
    finally:
        wire.close()
