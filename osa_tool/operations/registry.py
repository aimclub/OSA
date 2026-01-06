from abc import ABC
from typing import List, Optional

from osa_tool.osa_agent.models import Task
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

    # Order of execution (lower = earlier)
    priority: int = 100

    # Necessity of GitAgent
    uses_git: bool = False

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
        return [
            Task(
                id=self.name,
                description=self.description,
            )
        ]


class OperationRegistry:
    _operations: dict[str, Operation] = {}

    @classmethod
    def register(cls, operation: Operation):
        cls._operations[operation.name] = operation

    @classmethod
    def all(cls) -> list[Operation]:
        return list(cls._operations.values())

    @classmethod
    def get(cls, name: str) -> Optional[Operation]:
        return cls._operations.get(name)

    @classmethod
    def applicable(cls, state: OSAState) -> list[Operation]:
        return [op for op in cls._operations.values() if op.is_applicable(state)]
