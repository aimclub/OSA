import re
from typing import Any, Optional

from osa_tool.core.models.event import EventKind
from osa_tool.core.models.task import TaskStatus

FAILURE_STATUSES = {TaskStatus.FAILED, TaskStatus.PARTIAL}
_PRODUCTIVE_EVENTS = {
    EventKind.CREATED,
    EventKind.GENERATED,
    EventKind.SET,
    EventKind.REFINED,
    EventKind.UPDATED,
    EventKind.MOVED,
    EventKind.WRITTEN,
    EventKind.UPLOADED,
}

EXCLUDED_TASK = {
    "use_single_model",
    "config_file",
    "repository",
    "mode",
    "web_mode",
    "output",
    "branch",
    "based_on_date",
    "api",
    "base_url",
    "model",
    "model_docstring",
    "model_readme",
    "model_general",
    "model_repository_quality",
    "model_paper_claims",
    "model_paper_verification",
    "temperature",
    "max_tokens",
    "context_window",
    "top_p",
    "attachment",
    "delete_dir",
    "no_fork",
    "no_pull_request",
    "branches",
    "codecov_token",
    "max_retries",
    "artefacts_language",
    "scorecard",
}


class Plan:
    def __init__(self, generated_plan: dict):
        self.tasks: dict[str, TaskStatus] = {
            key: TaskStatus.PENDING for key, value in generated_plan.items() if self._is_active_task(key, value)
        }
        self.generated_plan = generated_plan
        self.results: dict[str, dict] = {}

    @staticmethod
    def _is_active_task(task: str, value: Any) -> bool:
        """Treat an empty notebook path list as a repository-wide scan."""
        return bool(value) or (task == "notebook_report" and value == [])

    @staticmethod
    def _normalize_result(result: Any) -> dict:
        if result is None:
            return {"result": None, "events": []}
        if isinstance(result, dict):
            return {
                "result": result.get("result"),
                "events": result.get("events", []),
            }
        return {"result": result, "events": []}

    def record_result(self, task: str, result: Any) -> None:
        """Store normalized result for a task, keyed by its human‑readable name."""
        self.results[task] = self._normalize_result(result)

    @staticmethod
    def _event_field(event: Any, field: str) -> Any:
        return event.get(field) if isinstance(event, dict) else getattr(event, field, None)

    def complete_operation(self, task: str, raw_result: Any) -> TaskStatus:
        """Record a terminal outcome for an operation that actually ran."""
        self.record_result(task, raw_result)
        outcome = self.results[task]
        events = outcome["events"] or []
        kinds = {self._event_field(event, "kind") for event in events}
        explicit_status = raw_result.get("status") if isinstance(raw_result, dict) else None
        if explicit_status is not None:
            status = TaskStatus(explicit_status)
        elif self.failure_reasons(task):
            status = TaskStatus.PARTIAL if kinds & _PRODUCTIVE_EVENTS else TaskStatus.FAILED
        elif kinds & {EventKind.SKIPPED, EventKind.EXISTS} and not kinds & _PRODUCTIVE_EVENTS:
            status = TaskStatus.SKIPPED
        else:
            status = TaskStatus.COMPLETED
        self.tasks[task] = status
        return status

    def failure_reasons(self, task: str) -> list[str]:
        outcome = self.results[task]
        payload = outcome["result"]
        reasons = []
        for event in outcome["events"] or []:
            if self._event_field(event, "kind") != EventKind.FAILED:
                continue
            data = self._event_field(event, "data") or {}
            if data.get("recovered"):
                continue
            detail = data.get("error") or data.get("stderr") or data.get("reason") or "Operation failed"
            target = self._event_field(event, "target")
            reasons.append(f"{target}: {detail}" if target else str(detail))
        if not reasons and isinstance(payload, dict) and "error" in payload:
            reasons.append(str(payload["error"]))
        return list(dict.fromkeys(self.brief_reason(reason) for reason in reasons))

    @staticmethod
    def brief_reason(reason: str) -> str:
        reason = re.sub(r"(https?://)[^/\s@]+@", r"\1***@", reason)
        return " ".join(reason.split())[:500]

    def operation_rows(self):
        """Yield recorded operation outcomes in execution order."""
        for task in self.results:
            yield task, self.tasks[task], self.failure_reasons(task)

    def get(self, task: str) -> Optional[Any]:
        return self.generated_plan.get(task, None)

    def mark_started(self, task: str):
        self.tasks[task] = TaskStatus.IN_PROGRESS

    def mark_done(self, task: str):
        self.tasks[task] = TaskStatus.COMPLETED

    def mark_failed(self, task: str):
        self.tasks[task] = TaskStatus.FAILED

    @property
    def list_for_report(self) -> list[tuple[str, bool]]:
        tasks = []
        for task in self.tasks.keys():
            if task not in EXCLUDED_TASK:
                tasks.append((task, self.tasks[task] == TaskStatus.COMPLETED))
        return tasks

    @staticmethod
    def _format_task_name(task: str) -> str:
        parts = task.split("_")
        if parts and parts[0]:
            parts[0] = parts[0][0].upper() + parts[0][1:]
        return " ".join(parts)
