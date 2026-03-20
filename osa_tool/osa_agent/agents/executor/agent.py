from typing import Any

from rich import box
from rich.table import Table

from osa_tool.core.models.agent_status import AgentStatus
from osa_tool.core.models.task import TaskStatus, Task
from osa_tool.operations.registry import OperationRegistry
from osa_tool.osa_agent.base import BaseAgent
from osa_tool.osa_agent.state import OSAState
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import rich_section, console


class ExecutorAgent(BaseAgent):
    """
    Agent responsible for executing planned tasks, orchestrating the systematic processing and enhancement of repository documentation and structure.
    
        The ExecutorAgent:
        - iterates over the execution plan
        - resolves executor dependencies and task arguments
        - invokes operation executors (function-style or class-style)
        - updates task statuses and stores execution results
        - persists artifacts into the shared agent state
    """


    name = "Executor"

    def run(self, state: OSAState) -> OSAState:
        """
        Execute all pending tasks in the current plan.
        
        Tasks are executed sequentially in plan order. Each task:
        - transitions through PENDING → IN_PROGRESS → COMPLETED / FAILED
        - stores its execution result in both the task and state artifacts
        
        Why: This method drives the sequential execution of the workflow plan, ensuring each pending task is processed, its status updated, and its results recorded for downstream use.
        
        Args:
            state: Current workflow state containing the execution plan. The method updates this state in place by setting the active agent, status, current step index, and artifacts.
        
        Returns:
            Updated state with executed tasks and collected artifacts. The state includes updated task statuses, results stored in artifacts, and logging information about execution outcomes.
        """
        rich_section("Executor Agent")
        state.active_agent = self.name
        state.status = AgentStatus.GENERATING

        pending_count = sum(1 for t in state.plan if t.status is TaskStatus.PENDING)
        logger.info("Executor started; %s pending tasks in plan", pending_count)
        self._render_plan_cli(state)

        for idx, task in enumerate(state.plan):
            if task.status is not TaskStatus.PENDING:
                continue

            state.current_step_index = idx
            self._run_task(task, state)

            state.artifacts[task.id] = {"result": task.result, "events": task.events}

        completed = sum(1 for t in state.plan if t.status is TaskStatus.COMPLETED)
        failed = sum(1 for t in state.plan if t.status is TaskStatus.FAILED)
        logger.info("Executor completed: %s succeeded, %s failed", completed, failed)
        return state

    def _run_task(self, task: Task, state: OSAState) -> None:
        """
        Execute a single task and update its lifecycle status.
        
        This method:
        - marks the task as IN_PROGRESS
        - executes the task via its registered operation executor
        - captures execution results or errors
        - updates task status accordingly
        
        WHY: This method centralizes task execution and error handling to ensure consistent state transitions and logging, which is critical for tracking workflow progress and diagnosing failures in the automated documentation pipeline.
        
        Args:
            task: Task to be executed. Its status, result, and events attributes are updated based on execution outcome.
            state: Current workflow state, providing context and data needed for task execution.
        
        The method does not return a value; it modifies the provided task object in place.
        """
        task.status = TaskStatus.IN_PROGRESS
        logger.info("Task '%s' in progress", task.id)

        try:
            result = self._execute_task(task, state)
            task.result = result.get("result")
            task.events = result.get("events", [])
            task.status = TaskStatus.COMPLETED
            logger.info("Task '%s' completed", task.id)

        except Exception as e:
            task.status = TaskStatus.FAILED

            if isinstance(e, dict):
                task.result = e.get("result")
                task.events = e.get("events", [])
            else:
                task.result = {"error": str(e)}
                task.events = []

            logger.error("Task '%s' failed: %s", task.id, e, exc_info=True)

    def _execute_task(self, task: Task, state: OSAState) -> dict[str, Any]:
        """
        Execute a task using its operation execution descriptor.
        
        This method:
        - resolves the operation executor from the OperationRegistry
        - injects dependencies from AgentContext and workflow state
        - supports both function-style and class-style executors
        - normalizes the execution result
        
        WHY: The method orchestrates task execution by dynamically resolving and injecting dependencies, allowing flexible executor definitions (functions or classes) to handle different operation types within the workflow.
        
        Args:
            task: Task to execute.
            state: Current workflow state.
        
        Returns:
            Normalized execution result.
        
        Raises:
            ValueError: If the operation has no executor or misconfigured method.
            TypeError: If the executor type is invalid.
        """
        desc = OperationRegistry.get_execution_descriptor(task.id)
        executor = desc["executor"]
        method_name = desc["method"]
        dependencies = desc["dependencies"]
        state_dependencies = desc["state_dependencies"]

        if executor is None:
            raise ValueError(f"No executor defined for operation '{task.id}'")

        # Resolve dependencies from AgentContext
        deps = {dep: getattr(self.context, dep) for dep in dependencies if hasattr(self.context, dep)}

        # Resolve dependencies from state
        state_args = {dep: getattr(state, dep) for dep in state_dependencies if hasattr(state, dep)}

        # Merge task args
        args = {**(deps or {}), **(state_args or {}), **(task.args or {})}

        # Function-style executor
        if callable(executor) and method_name is None:
            result = executor(**args)

        # Class-style executor
        elif isinstance(executor, type):
            agent_instance = executor(**args)
            if not method_name:
                raise ValueError(f"executor_method must be defined for class-style executor '{task.id}'")
            method = getattr(agent_instance, method_name)
            result = method()

        else:
            raise TypeError(f"Invalid executor type for task '{task.id}': {type(executor)}")

        return self._normalize_result(result)

    @staticmethod
    def _normalize_result(result) -> dict:
        """
        Normalize executor output to a consistent dictionary format.
        
        Ensures uniform task result structure regardless of executor return type,
        which simplifies downstream processing and error handling. This is necessary
        because executors may return raw values, dictionaries, or None.
        
        Args:
            result: Raw executor result. Can be any type, including None.
        
        Returns:
            dict: Normalized dictionary with keys:
                - "result": The extracted or original result value.
                - "events": A list of events; defaults to an empty list if not provided.
        
        Behavior:
            - If result is None, returns {"result": None, "events": []}.
            - If result is a dict, extracts "result" and "events" keys (defaulting events to [] if missing).
            - Otherwise, treats the entire result as the value for "result" with empty events.
        """
        if result is None:
            return {"result": None, "events": []}

        if isinstance(result, dict):
            return {
                "result": result.get("result"),
                "events": result.get("events", []),
            }

        return {"result": result, "events": []}

    @staticmethod
    def _render_plan_cli(state: OSAState) -> None:
        """
        Render execution plan as a Rich table for CLI users.
        
        Args:
            state: Current workflow state containing the plan and reasoning to display.
        
        WHY:
            This method provides a visual summary of the execution plan directly in the terminal, helping CLI users understand the upcoming tasks and the planner's reasoning before execution begins. It enhances user visibility into the workflow.
        
        Details:
            - If no plan exists, an error message is printed and the method returns early.
            - A formatted table is built showing each task's sequence number, ID, and special arguments.
            - If planner reasoning is available in the state, it is displayed separately below the table.
        """
        if not state.plan:
            console.print("[bold red]No tasks in the execution plan.[/]")
            return

        table = Table(
            title="Execution Plan",
            box=box.ROUNDED,
            show_lines=True,
            title_style="bold cyan",
            header_style="bold white",
        )

        table.add_column("#", justify="right", style="bold yellow")
        table.add_column("Task ID", style="bold")
        table.add_column("Special Arguments", style="dim")

        for i, task in enumerate(state.plan, start=1):
            table.add_row(
                str(i),
                f"[cyan]{task.id}[/]",
                str(task.args),
            )

        console.print(table)

        if state.plan_reasoning:
            console.print("\n[bold cyan]Planner Reasoning[/]:")
            console.print(f"[dim]{state.plan_reasoning}[/]")
