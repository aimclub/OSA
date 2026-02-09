from abc import ABC
from typing import List, Optional, Type, Union, Callable, Any

from pydantic import BaseModel

from osa_tool.core.models.task import Task
from osa_tool.osa_agent.state import OSAState


class Operation(ABC):
    """
    Declarative description of an operation.
    """

    # Identity
    name: str
    description: str

    # Planning
    supported_intents: List[str]
    supported_scopes: List[str]
    # possible values:
    # - "analysis"  # only analysis, reports
    # - "docs",  # documentation (README, LICENSE, community, about)
    # - "codebase",  # code + structure + files
    # - "full_repo",  # all
    priority: int = 100  # order of execution (lower = earlier)
    args_schema: Optional[Type[BaseModel]] = None
    args_policy: str = "auto"
    # possible values:
    # - "auto"           = infer silently
    # - "ask_if_missing" = WAITING_FOR_USER
    # - "required"       = error if not resolved
    prompt_for_args: Optional[str] = None

    # Execution
    executor: Optional[Union[Callable[..., Any], Type[Any]]] = None
    executor_method: Optional[str] = None  # class-style method
    executor_dependencies: List[str] = []
    state_dependencies: List[str] = []

    def is_applicable(self, state: OSAState) -> bool:
        """
        Hard constraints:
        - intent
        - scope
        """
        if state.intent not in self.supported_intents:
            return False

        if self.supported_scopes and state.task_scope not in self.supported_scopes:
            return False

        return True

    def plan_tasks(self) -> List[Task]:
        """
        Prototype-level planning:
        1 operation = 1 task
        """
        return [Task(id=self.name, description=self.description)]


class OperationRegistry:
    _operations: dict[str, Operation] = {}

    @classmethod
    def register(cls, operation: Operation):
        cls._operations[operation.name] = operation

    @classmethod
    def get(cls, name: str) -> Optional[Operation]:
        return cls._operations.get(name)

    @classmethod
    def list_all(cls) -> list[Operation]:
        return list(cls._operations.values())

    @classmethod
    def applicable(cls, state: OSAState) -> list[Operation]:
        return [op for op in cls._operations.values() if op.is_applicable(state)]

    @classmethod
    def get_execution_descriptor(cls, name: str) -> dict:
        """
        Returns a descriptor for execution with keys:
        - executor: callable or class
        - method: method name if class-style
        - dependencies: list of names to extract from AgentContext
        """
        op = cls.get(name)
        if not op:
            raise ValueError(f"Unknown operation {name}")
        return {
            "executor": op.executor,
            "dependencies": op.executor_dependencies,
            "state_dependencies": op.state_dependencies,
            "method": op.executor_method,
        }
