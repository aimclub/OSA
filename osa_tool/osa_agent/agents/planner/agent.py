from typing import List

from langchain_core.output_parsers import PydanticOutputParser

from osa_tool.core.models.agent import AgentStatus
from osa_tool.operations.operations_catalog import register_all_operations
from osa_tool.operations.registry import OperationRegistry, Operation
from osa_tool.osa_agent.agents.planner.models import PlannerDecision, ArgumentDetectionResponse
from osa_tool.osa_agent.base import BaseAgent
from osa_tool.osa_agent.state import OSAState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.utils import rich_section


class PlannerAgent(BaseAgent):
    """
    Agent responsible for planning the execution workflow.

    The PlannerAgent:
    - selects applicable operations based on the current state
    - decides which operations should be executed
    - builds an ordered execution plan
    - detects and injects additional arguments required by operations
    """

    name = "Planner"

    def run(self, state: OSAState) -> OSAState:
        """
        Execute the planning phase of the workflow.

        This method:
        1. Retrieves all applicable operations
        2. Uses an LLM to decide which operations to run
        3. Builds an ordered task plan
        4. Detects and assigns required operation arguments
        5. Updates workflow state and session memory

        Args:
            state (OSAState): Current workflow state.

        Returns:
            OSAState: Updated state containing the execution plan.
        """
        rich_section("Planner Agent")
        state.active_agent = self.name
        state.status = AgentStatus.GENERATING

        register_all_operations()
        available_ops = OperationRegistry.applicable(state)

        decision = self._plan(state, available_ops)
        selected_ops = self._select_operations(decision)

        self._build_plan(state, selected_ops)
        detect_args_prompt = self._detect_additional_arguments(state)

        state.current_step_index = 0

        state.session_memory.append(
            {
                "agent": self.name,
                "decision": decision.model_dump(),
                "plan": [t.model_dump() for t in state.plan],
                "detect_args_prompt": detect_args_prompt,
            }
        )

        logger.debug(state)

        return state

    def _plan(self, state: OSAState, available_ops: List[Operation]) -> PlannerDecision:
        """
        Use the language model to decide which operations should be executed.

        Args:
            state (OSAState): Current workflow state.
            available_ops (list[Operation]): Operations applicable to the current state.

        Returns:
            PlannerDecision: Model output describing selected operations.
        """
        parser = PydanticOutputParser(pydantic_object=PlannerDecision)

        system_message = PromptBuilder.render(
            self.context.prompts.get("system_messages.planner"),
            safe=True,
        )

        prompt = PromptBuilder.render(
            self.context.prompts.get("osa_agent.planner"),
            user_request=state.user_request,
            intent=state.intent,
            task_scope=state.task_scope,
            repo_data=state.repo_data,
            available_operations="\n".join(f"- {op.name}: {op.description}" for op in available_ops),
        )

        return self.context.model_handler.run_chain(
            prompt=prompt,
            parser=parser,
            system_message=system_message,
        )

    @staticmethod
    def _select_operations(decision: PlannerDecision) -> List[Operation]:
        """
        Resolve and sort selected operations based on priority.

        Args:
            decision (PlannerDecision): Planner decision containing operation names.

        Returns:
            list[Operation]: Sorted list of operation descriptors.
        """
        ops = [OperationRegistry.get(name) for name in decision.operations if OperationRegistry.get(name)]
        ops.sort(key=lambda op: op.priority)
        return ops

    def _build_plan(self, state: OSAState, operations) -> None:
        """
        Build the task execution plan from selected operations.

        This method also tracks operations that require additional arguments
        for later argument detection.

        Args:
            state (OSAState): Current workflow state.
            operations (list[Operation]): Selected operations.
        """
        state.plan = []
        self._operations_with_args = []

        for op in operations:
            tasks = op.plan_tasks()
            if op.args_schema:
                self._operations_with_args.append(op)
            state.plan.extend(tasks)

    def _detect_additional_arguments(self, state: OSAState) -> str:
        """
        Detect and assign additional arguments required by operations.

        Uses an LLM to infer missing or optional arguments based on
        the user's request and operation prompts.

        Args:
            state (OSAState): Current workflow state.

        Returns:
            str: Prompt used for argument detection (for debugging / traceability).
        """
        if not self._operations_with_args:
            return ""

        parser = PydanticOutputParser(pydantic_object=ArgumentDetectionResponse)

        system_message = PromptBuilder.render(
            self.context.prompts.get("system_messages.detect_arguments"),
            safe=True,
        )

        operations_str = "\n".join(f"- {op.name}: {op.prompt_for_args}" for op in self._operations_with_args)

        prompt = PromptBuilder.render(
            self.context.prompts.get("osa_agent.detect_arguments"),
            user_request=state.user_request,
            operations=operations_str,
        )

        response = self.context.model_handler.run_chain(
            prompt=prompt,
            parser=parser,
            system_message=system_message,
        )

        for op_name, args in response.root.items():
            for task in state.plan:
                if task.id == op_name:
                    task.args.update(args)

        return prompt
