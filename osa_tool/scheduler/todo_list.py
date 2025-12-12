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
    "codecov_token"
}


class ToDoList:
    def __init__(self, plan: dict[str, bool]):
        self.plan = {key for key in plan if plan[key]}
        self.did: set[str] = set()

    def mark_did(self, task: str):
        self.did.add(task)

    @property
    def list_for_report(self) -> list[tuple[str, bool]]:
        tasks = []
        for planned in self.plan:
            if planned not in EXCLUDED_TASK:
                formatted_name = planned.split("_")
                formatted_name[0] = formatted_name[0][0].upper() + formatted_name[0][1:]
                tasks.append((' '.join(formatted_name), planned in self.did))
        return tasks
