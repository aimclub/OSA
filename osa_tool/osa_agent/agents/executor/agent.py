from osa_tool.core.models.agent import AgentStatus
from osa_tool.core.models.task import TaskStatus, Task
from osa_tool.operations.registry import OperationRegistry
from osa_tool.osa_agent.base import BaseAgent
from osa_tool.osa_agent.state import OSAState
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import rich_section


class ExecutorAgent(BaseAgent):
    """
    ExecutorAgent is responsible for executing tasks in the agent's plan.

    It iterates over the tasks in the plan, resolves their arguments,
    calls the executor (function or class-style), and updates task status
    and results. All results are also stored in the state's artifacts.
    """

    name = "Executor"

    def run(self, state: OSAState) -> OSAState:
        """
        Runs all pending tasks in the current state.

        Args:
            state (OSAState): The current agent state containing the plan.

        Returns:
            OSAState: Updated state with tasks executed and results saved.
        """
        rich_section("Executor Agent")

        state.active_agent = self.name
        state.status = AgentStatus.GENERATING

        for idx, task in enumerate(state.plan):
            if task.status is not TaskStatus.PENDING:
                continue

            state.current_step_index = idx
            self._run_task(task, state)

            state.artifacts[task.id] = task.result

        return state

    def _run_task(self, task: Task, state: OSAState):
        """
        Executes a single task and updates its status.

        Args:
            task (Task): Task to execute.
            state (OSAState): The current agent state containing the plan.
        """
        task.status = TaskStatus.IN_PROGRESS
        logger.info(f"Task '{task.id}' in progress")

        try:
            result = self._execute_task(task, state)
            task.result = result
            task.status = TaskStatus.COMPLETED
            logger.info(f"Task '{task.id}' completed")

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.result = {"error": str(e)}
            logger.error(f"Task '{task.id}' failed", exc_info=True)

    def _execute_task(self, task: Task, state: OSAState) -> dict:
        """
        Executes a single task based on its operation descriptor from OperationRegistry.

        Supports function-style and class-style executors. Dependencies are automatically
        resolved from the agent's context based on executor_dependencies.

        Args:
            task (Task): Task to execute.
            state (OSAState): The current agent state containing the plan.

        Returns:
            dict: The execution result.
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
        Ensures task.result is always a dict.

        Args:
            result (Any): Result returned by the executor.

        Returns:
            dict: Normalized result.
        """
        if result is None:
            return {}

        if isinstance(result, dict):
            return result

        return {"result": result}
