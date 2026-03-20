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
    """
    A class that manages and tracks the execution status of tasks within a generated plan.
    
        Attributes:
            tasks: A mapping of task identifiers to their current status, initialized to PENDING for all valid tasks in the plan.
            generated_plan: The original dictionary containing the task definitions and structure.
            results: A dictionary used to store the execution results of each task.
    
        Methods:
            __init__: Initializes a new instance of the class with a generated plan.
            _normalize_result: Normalizes the output of a task execution into a standard dictionary format.
            record_result: Stores normalized result for a task, keyed by its human‑readable name.
            get: Retrieves the value associated with a specific task from the generated plan.
            mark_started: Updates the status of a specific task to indicate it has started.
            mark_done: Marks a specific task as completed.
            mark_failed: Marks a specific task as failed in the task tracker.
            list_for_report: Generates a list of tasks formatted for reporting purposes.
            _format_task_name: Formats a task name by converting it from snake_case to a capitalized string.
    """

    def __init__(self, generated_plan: dict):
        """
        Initialize a new instance of the Plan class with a generated plan.
        
        Args:
            generated_plan: A dictionary representing the plan where keys are task identifiers.
                Each key's value should be truthy (non-empty) to be considered a valid task.
                Tasks with falsy values (e.g., empty dict, None, False) are excluded from the task list.
        
        Attributes:
            tasks: A mapping of task identifiers to their current status, initialized to PENDING for all valid tasks in the plan.
                Only tasks with truthy values in `generated_plan` are included.
            generated_plan: The original dictionary containing the task definitions and structure.
            results: A dictionary used to store the execution results of each task, initially empty.
        """
        self.tasks: dict[str, TaskStatus] = {key: TaskStatus.PENDING for key in generated_plan if generated_plan[key]}
        self.generated_plan = generated_plan
        self.results: dict[str, dict] = {}

    @staticmethod
    def _normalize_result(result: Any) -> dict:
        """
        Normalizes the output of a task execution into a standard dictionary format.
                
                This ensures all task results have a consistent structure for downstream processing,
                regardless of the raw output type. This is necessary because tasks can return
                various data types (None, dict, or simple values), but the pipeline expects a
                uniform format.
                
                Args:
                    result: The raw output from a task execution, which could be None, a dictionary,
                        or a simple value (e.g., str, int, list).
                
                Returns:
                    dict: A dictionary with two keys:
                        - 'result': The normalized result value. If the input is a dictionary,
                          this extracts the value under the 'result' key; otherwise, it uses the
                          input directly (or None if input is None).
                        - 'events': A list of events extracted from the input dictionary if present;
                          otherwise, an empty list.
                
                Examples of normalization:
                    - None -> {"result": None, "events": []}
                    - {"result": "data", "events": ["event1"]} -> {"result": "data", "events": ["event1"]}
                    - {"result": "data"} -> {"result": "data", "events": []}
                    - "simple output" -> {"result": "simple output", "events": []}
                    - 123 -> {"result": 123, "events": []}
        """
        if result is None:
            return {"result": None, "events": []}
        if isinstance(result, dict):
            return {
                "result": result.get("result"),
                "events": result.get("events", []),
            }
        return {"result": result, "events": []}

    def record_result(self, task: str, result: Any) -> None:
        """
        Store a normalized result for a task, keyed by its human‑readable name.
        
        This method is used to persist the outcome of a task after processing, making it
        available for later reference or reporting within the plan. Results are stored
        in a normalized form to ensure consistency and are indexed by a formatted,
        human‑readable version of the task name for clarity.
        
        Args:
            task: The identifier or name of the task whose result is being recorded.
            result: The raw result data to be stored; it will be normalized before storage.
        
        Why:
            The method normalizes the result to maintain a uniform data format across
            different tasks, which simplifies later retrieval and usage. The task name
            is formatted into a display-friendly version to improve readability in
            reports or logs.
        """
        display_name = self._format_task_name(task)
        self.results[display_name] = self._normalize_result(result)

    def get(self, task: str) -> Optional[Any]:
        """
        Retrieve the value associated with a specific task from the generated plan.
        
        This method provides safe access to the internal plan dictionary, returning None if the task is not found instead of raising a KeyError. It is used to query the outcomes or details of tasks that have been planned or executed.
        
        Args:
            task: The key representing the task to look up in the plan.
        
        Returns:
            Optional[Any]: The value associated with the task if it exists, otherwise None.
        """
        return self.generated_plan.get(task, None)

    def mark_started(self, task: str):
        """
        Updates the status of a specific task to indicate it has started.
        This method is used to transition a task from a pending or other state to an in‑progress state, enabling progress tracking within the overall plan.
        
        Args:
            task: The identifier or name of the task to be marked as in progress. This key must already exist in the task dictionary.
        
        Raises:
            KeyError: If the provided task identifier is not found in the task dictionary.
        
        Note:
            The method directly modifies the internal task dictionary by setting the status of the specified task to `TaskStatus.IN_PROGRESS`.
        """
        self.tasks[task] = TaskStatus.IN_PROGRESS

    def mark_done(self, task: str):
        """
        Marks a specific task as completed and updates its status in the task dictionary.
        
        Args:
            task: The name or identifier of the task to be updated.
        
        Returns:
            None.
        
        Why:
            This method updates the internal task tracking by setting the specified task's status to COMPLETED. It ensures that task progress is recorded within the Plan instance, which is essential for tracking completion states in the overall documentation or enhancement pipeline.
        """
        self.tasks[task] = TaskStatus.COMPLETED

    def mark_failed(self, task: str):
        """
        Marks a specific task as failed in the task tracker.
        This updates the internal task state to reflect a failure, which is used to track the completion status of operations within the plan.
        
        Args:
            task: The identifier or name of the task to be updated.
        
        Returns:
            None.
        """
        self.tasks[task] = TaskStatus.FAILED

    @property
    def list_for_report(self) -> list[tuple[str, bool]]:
        """
        Generates a list of tasks formatted for reporting purposes.
        
        This property iterates through the instance's tasks, filters out excluded tasks, and formats their names. Each task is represented as a tuple containing its display name and a boolean indicating whether it has been completed.
        
        WHY: This method is used to produce a clean, presentation-ready list of tasks, omitting internal or administrative tasks (defined in EXCLUDED_TASK) and applying consistent naming formatting for reports.
        
        Returns:
            list[tuple[str, bool]]: A list of tuples where each tuple contains the formatted task name (str) and its completion status (bool).
        """
        tasks = []
        for task in self.tasks.keys():
            if task not in EXCLUDED_TASK:
                display_name = self._format_task_name(task)
                tasks.append((display_name, self.tasks[task] == TaskStatus.COMPLETED))
        return tasks

    @staticmethod
    def _format_task_name(task: str) -> str:
        """
        Formats a task name by converting it from snake_case to a capitalized string.
        
        The method splits the input string by underscores, capitalizes the first letter of the first word, and joins the parts with spaces. This formatting is used to present internal task identifiers (which are often in snake_case for code consistency) in a more human-readable form for documentation or display purposes.
        
        Args:
            task: The task name string to be formatted, expected to be in snake_case.
        
        Returns:
            str: The formatted task name with the first word capitalized and underscores replaced by spaces. If the input is an empty string or starts with an underscore, the first word will be capitalized appropriately if possible.
        """
        parts = task.split("_")
        if parts and parts[0]:
            parts[0] = parts[0][0].upper() + parts[0][1:]
        return " ".join(parts)
