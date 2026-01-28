from enum import Enum
from typing import Optional, Any

EXCLUDED_TASK = {
    "repository",
    "mode",
    "web_mode",
    "output",
    "branch",
    "api",
    "base_url",
    "model",
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


class TaskStatus(Enum):
    SCHEDULED = "SCHEDULED"
    STARTED = "STARTED"
    DONE = "DONE"
    FAILED = "FAILED"


class Plan:
    def __init__(self, generated_plan: dict):
        self.tasks: dict[str, TaskStatus] = {key: TaskStatus.SCHEDULED for key in generated_plan if generated_plan[key]}
        self.generated_plan = generated_plan

    def status(self, task: str) -> TaskStatus:
        return self.tasks[task]

    def get(self, task: str) -> Optional[Any]:
        return self.generated_plan.get(task, None)

    def mark_started(self, task: str):
        self.tasks[task] = TaskStatus.STARTED

    def mark_done(self, task: str):
        self.tasks[task] = TaskStatus.DONE

    def mark_failed(self, task: str):
        self.tasks[task] = TaskStatus.FAILED

    @property
    def list_for_report(self) -> list[tuple[str, bool]]:
        tasks = []
        for task in self.tasks.keys():
            if task not in EXCLUDED_TASK:
                formatted_name = task.split("_")
                formatted_name[0] = formatted_name[0][0].upper() + formatted_name[0][1:]
                tasks.append((" ".join(formatted_name), self.tasks[task] == TaskStatus.DONE))
        return tasks
