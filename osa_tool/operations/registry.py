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

    # Execution
    executor: Optional[Union[Callable[..., Any], Type[Any]]] = None
    executor_method: Optional[str] = None  # class-style method
    executor_dependencies: List[str] = []
    state_dependencies: List[str] = []

    def is_applicable(self, state: OSAState) -> bool:
        """
        Check if this operation can be applied to the given state based on hard constraints.
        
        The operation is applicable only if the state's intent matches one of the operation's supported intents,
        and if the state's task scope is among the operation's supported scopes (when supported scopes are defined).
        This ensures the operation is only used in appropriate contexts, preventing misapplication.
        
        Args:
            state: The current OSA state containing intent and task scope to evaluate.
        
        Returns:
            True if the operation can be applied to the state, False otherwise.
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
        
        WHY: This is a simple initial implementation where each operation directly maps to a single task, avoiding complex planning logic during early development.
        
        Args:
            self: The operation instance.
        
        Returns:
            A list containing exactly one task, with the task's id set to the operation's name and its description set to the operation's description.
        """
        return [Task(id=self.name, description=self.description)]


class OperationRegistry:
    """
    Registry for managing and retrieving operations.
    
        This class maintains a collection of operations that can be registered,
        retrieved, and filtered based on applicability to specific states.
    
        Attributes:
            _operations: Dictionary mapping operation names to operation instances.
    
        Methods:
            register: Registers a new operation within the class's operation registry.
            get: Retrieves an operation by its name from the registered operations.
            list_all: Retrieves all registered operations.
            applicable: Determines which operations from the class's collection can be applied to the given state.
            get_execution_descriptor: Returns a descriptor for execution with executor, method, and dependency information.
    """

    _operations: dict[str, Operation] = {}

    @classmethod
    def register(cls, operation: Operation):
        """
        Registers a new operation within the class's operation registry.
        This is a class method that adds the operation to the internal registry dictionary, keyed by the operation's name, making it available for later lookup and execution.
        
        Args:
            operation: The operation object to be registered, which must have a name attribute. The operation is stored under its name in the registry.
        
        Returns:
            None: This method does not return a value.
        """
        cls._operations[operation.name] = operation

    @classmethod
    def get(cls, name: str) -> Optional[Operation]:
        """
        Retrieves an operation by its name from the registered operations.
        
        This is a class method that accesses the internal registry (`_operations`) to look up an operation. It is used to obtain a specific operation instance by its unique name, enabling dynamic access and execution within the OSA Tool's pipeline.
        
        Args:
            name: The name of the operation to retrieve.
        
        Returns:
            Optional[Operation]: The operation associated with the given name, or None if not found.
        """
        return cls._operations.get(name)

    @classmethod
    def list_all(cls) -> list[Operation]:
        """
        Retrieves all registered operations from the class registry.
        
        This is a class method that provides access to the complete collection of operations stored in the registry. It is primarily used to inspect or iterate over all available operations, for example, when generating documentation or validating the set of registered operations.
        
        Args:
            cls: The class object (OperationRegistry class itself).
        
        Returns:
            list[Operation]: A list containing all operation instances stored in the registry, in the order they were registered (preserving insertion order as of Python 3.7+ dict behavior).
        """
        return list(cls._operations.values())

    @classmethod
    def applicable(cls, state: OSAState) -> list[Operation]:
        """
        Determines which operations from the class's collection can be applied to the given state.
        This is a class method that filters the registry's stored operations based on whether each operation's specific constraints are satisfied by the current state.
        
        Args:
            state: The current state object used to evaluate the applicability of operations.
        
        Returns:
            list[Operation]: A list of operation instances that satisfy the necessary constraints for the provided state. The method checks each operation's `is_applicable` method, which enforces hard constraints (such as intent and scope) against the state.
        """
        return [op for op in cls._operations.values() if op.is_applicable(state)]

    @classmethod
    def get_execution_descriptor(cls, name: str) -> dict:
        """
        Returns a descriptor for execution with keys:
        - executor: callable or class
        - method: method name if class-style
        - dependencies: list of names to extract from AgentContext
        - state_dependencies: list of names to extract from AgentState
        
        Args:
            name: The name of the operation to look up.
        
        Returns:
            A dictionary descriptor containing the executor, its dependencies, state dependencies, and method name.
        
        Raises:
            ValueError: If the operation name is not found in the registry.
        
        Why:
            This descriptor is used to configure how an operation is executed, specifying what to run and what data it requires from the AgentContext and AgentState. This allows the execution engine to properly inject dependencies before running the operation.
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
