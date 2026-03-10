from typing import Optional, Any

from osa_tool.core.models.task import TaskStatus

EXCLUDED_TASK = {
    "use_single_model",
    "config_file",
    "repository",
    "mode",
    "web_mode",
    "output",
    "branch",
    "api",
    "base_url",
    "model",
    "model_docstring",
    "model_readme",
    "model_validation",
    "model_general",
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
}


class Plan:
    def __init__(self, generated_plan: dict):
        self.tasks: dict[str, TaskStatus] = {key: TaskStatus.PENDING for key in generated_plan if generated_plan[key]}
        self.generated_plan = generated_plan
        self.results: dict[str, dict] = {}

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
        display_name = self._format_task_name(task)
        self.results[display_name] = self._normalize_result(result)

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
                display_name = self._format_task_name(task)
                tasks.append((display_name, self.tasks[task] == TaskStatus.COMPLETED))
        return tasks

    @staticmethod
    def _format_task_name(task: str) -> str:
        parts = task.split("_")
        if parts and parts[0]:
            parts[0] = parts[0][0].upper() + parts[0][1:]
        return " ".join(parts)
