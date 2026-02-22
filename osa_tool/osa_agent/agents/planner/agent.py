from typing import List, get_origin, Literal, get_args

from langchain_core.output_parsers import PydanticOutputParser
from pydantic.fields import FieldInfo

from osa_tool.core.models.agent_status import AgentStatus
from osa_tool.operations.operations_catalog import register_all_operations
from osa_tool.operations.registry import OperationRegistry, Operation
from osa_tool.osa_agent.agents.planner.models import PlannerDecision, ArgumentDetectionResponse
from osa_tool.osa_agent.base import BaseAgent
from osa_tool.osa_agent.state import OSAState
from osa_tool.ui.input_for_chat import wait_for_user_clarification
from osa_tool.utils.logger import logger
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

        if state.status == AgentStatus.WAITING_FOR_USER and state.clarification_agent == self.name:
            logger.info("Planner handling missing argument clarification (loop)...")
            self._clarification_loop(state)
            return state

        state.status = AgentStatus.ANALYZING
        logger.info("Planner started.")
        register_all_operations()

        # Maintain plan history when re-planning after review: append last plan or clear for new request
        if state.active_request_source == "reviewer" and state.plan:
            state.plan_history = list(state.plan_history) + [[t.model_dump() for t in state.plan]]
            logger.debug(f"Appended current plan to plan_history ({len(state.plan_history)} prior plans).")
        else:
            state.plan_history = []
            logger.debug("Cleared plan_history (new request or first plan).")

        available_ops = self._get_available_operations(state)
        logger.debug(f"Available operations: {[op.name for op in available_ops]}")

        decision = self._make_decision(state, available_ops)
        state.plan_reasoning = (decision.reasoning or "").strip()
        selected_ops = self._select_operations(decision)
        logger.info(f"LLM selected operations: {[op.name for op in selected_ops]}")

        self._build_execution_plan(state, selected_ops)
        logger.debug(f"Initial plan tasks: {[t.id for t in state.plan]}")

        detect_args_prompt = self._detect_additional_arguments(state)
        logger.debug(f"Argument detection prompt used: {detect_args_prompt}")

        self._fill_default_args(state)
        logger.debug(
            "Task args after filling defaults:\n" + "\n".join(f"{task.id}: {task.args}" for task in state.plan)
        )

        if self._check_missing_args(state):
            return state

        state.current_step_index = 0
        state.status = AgentStatus.ANALYZING

        state.session_memory.append(
            {
                "agent": self.name,
                "active_request": state.active_request,
                "active_request_source": state.active_request_source,
                "intent": state.intent,
                "task_scope": state.task_scope,
                "repo_prepared": state.repo_prepared,
                "available_operations": [op.name for op in available_ops],
                "selected_operations": [op.name for op in selected_ops],
                "decision": decision.model_dump(),
                "plan": [t.model_dump() for t in state.plan],
                "operations_requiring_args": [op.name for op in self._operations_with_args],
                "default_args_applied": {task.id: task.args for task in state.plan},
                "new_status": state.status,
            }
        )
        logger.debug(f"Session memory updated with Planner step.")
        logger.debug(state)
        logger.info(f"Planner completed. Selected {len(selected_ops)} operations, built {len(state.plan)} tasks.")

        return state

    @staticmethod
    def _get_available_operations(state: OSAState) -> List[Operation]:
        """Retrieves all applicable operations"""
        return OperationRegistry.applicable(state)

    @staticmethod
    def _format_plan_history_section(plan_history: List[List[dict]]) -> str:
        """
        Format plan_history for the planner prompt so the LLM sees which plans were already tried.
        Returns an empty string when there is no history.
        """
        if not plan_history:
            return ""
        lines = []
        for i, plan in enumerate(plan_history, start=1):
            task_ids = [t.get("id", "?") for t in plan]
            lines.append(f"- Cycle {i}: {', '.join(task_ids)}")
        return "Previous plans from this review loop (not approved by the user):\n" + "\n".join(lines) + "\n\n"

    def _make_decision(self, state: OSAState, available_ops: List[Operation]) -> PlannerDecision:
        """
        Use the language model to decide which operations should be executed.

        Args:
            state (OSAState): Current workflow state.
            available_ops (list[Operation]): Operations applicable to the current state.

        Returns:
            PlannerDecision: Model output describing selected operations.
        """
        parser = PydanticOutputParser(pydantic_object=PlannerDecision)
        system_message = self._render("system_messages.planner", safe=True)
        prompt = self._render(
            "osa_agent.planner",
            active_request=state.active_request,
            intent=state.intent,
            task_scope=state.task_scope,
            plan_history_section=self._format_plan_history_section(state.plan_history),
            repo_data=state.repo_data,
            available_operations="\n".join(f"- {op.name}: {op.description}" for op in available_ops),
        )
        logger.debug(f"Planner _make_decision prompt:\n{prompt}")
        return self._run_llm(prompt, parser, system_message)

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

    def _build_execution_plan(self, state: OSAState, operations: List[Operation]) -> None:
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
            state.plan.extend(op.plan_tasks())
            if op.args_schema:
                self._operations_with_args.append(op)

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
        system_message = self._render("system_messages.detect_arguments", safe=True)

        operations_str_list = []
        for op in self._operations_with_args:
            field_prompts = [
                f"{fname}: {self._build_prompt_for_field(fdef)}" for fname, fdef in op.args_schema.model_fields.items()
            ]
            operations_str_list.append(f"- {op.name}:\n  " + "\n  ".join(field_prompts))
        operations_str = "\n".join(operations_str_list)

        prompt = self._render(
            "osa_agent.detect_arguments",
            active_request=state.active_request,
            operations=operations_str,
        )

        response = self._run_llm(prompt, parser, system_message)
        logger.debug(f"_detect_additional_arguments LLM output: {response.root}")

        for op_name, args in response.root.items():
            task = state.get_task(op_name)
            if not task:
                logger.warning(f"_detect_additional_arguments: unknown operation '{op_name}' in LLM output")
                continue

            if not isinstance(args, dict):
                logger.warning(f"_detect_additional_arguments: invalid args for '{op_name}': {args}")
                continue

            task.args.update(args)
            logger.debug(f"_detect_additional_arguments -> task '{task.id}' updated args: {task.args}")

        return prompt

    def _fill_default_args(self, state: OSAState) -> None:
        """
        Sets default argument values for operations if LLM returns nothing and args_policy == 'auto'.
        """
        if not self._operations_with_args:
            return

        for op in self._operations_with_args:
            task = state.get_task(op.name)

            if not task or task.args or op.args_policy != "auto":
                continue

            default_args_obj = op.args_schema()
            for k, v in default_args_obj.model_dump().items():
                task.args[k] = v
                logger.debug(f"_fill_default_args -> task '{task.id}' field '{k}' set to default '{v}'")

    def _check_missing_args(self, state: OSAState) -> bool:
        """
        Checks whether there are any unfilled required arguments with args_policy == 'ask_if_missing'.
        Prepares state for multi-question clarification via LLM.

        Returns True if clarification is required from the user.
        """
        if not self._operations_with_args:
            return False

        missing = []

        for op in self._operations_with_args:
            if op.args_policy != "ask_if_missing":
                continue

            task = state.get_task(op.name)
            if not task:
                continue

            provided_args = task.args or {}

            for field_name, field_def in op.args_schema.model_fields.items():
                if not field_def.is_required():
                    continue
                if field_name in provided_args:
                    continue

                prompt_text = self._build_prompt_for_field(field_def)
                missing.append(
                    {
                        "task_id": task.id,
                        "field": field_name,
                        "prompt": prompt_text,
                        "required": True,
                    }
                )
                logger.debug(f"_task_with_unfilled_required_args: {missing[-1]}")

        if not missing:
            return False

        # Save missing arguments in state
        state.missing_arguments = missing

        # Prepare clarification payload for LLM or multi-question UI
        state.clarification_required = True
        state.clarification_agent = self.name
        state.clarification_type = "multi_question"
        state.clarification_payload = {
            "question": "Several operations require additional information.",
            "fields": [
                {
                    "name": f"{item['task_id']}::{item['field']}",
                    "prompt": item["prompt"],
                    "required": item.get("required", True),
                }
                for item in missing
            ],
        }

        state.status = AgentStatus.WAITING_FOR_USER
        logger.warning(f"Some arguments are missing: {[item['field'] for item in missing]}")
        logger.debug(f"Agents state after detecting missing arguments: {state}")

        return True

    def _clarification_loop(self, state: OSAState):
        """
        Loop to handle missing arguments clarification from the user.
        Uses LLM to validate/convert user's answers into proper task.args.
        Stops if all missing arguments are filled or max attempts are reached.
        """

        attempts = 0
        max_attempts = getattr(state, "clarification_attempts", 3)

        while attempts < max_attempts:
            attempts += 1
            logger.info(f"Clarification attempt {attempts} of {max_attempts}")

            # Ask user for missing arguments
            answers = wait_for_user_clarification(state)

            # Apply LLM to process answers and update task.args
            self._apply_clarification_via_llm(state, answers)

            # Check which arguments are still missing
            still_missing = [item for item in state.missing_arguments if not self._task_has_arg(state, item)]

            if not still_missing:
                # All arguments filled successfully
                state.missing_arguments = []
                self._reset_clarification(state)
                state.status = AgentStatus.ANALYZING
                logger.info("All missing arguments filled successfully.")
                return

            # Update state for next attempt
            state.missing_arguments = still_missing
            state.clarification_payload = {
                "question": "Several operations still require information.",
                "fields": [
                    {"name": f"{item['task_id']}::{item['field']}", "prompt": item["prompt"], "required": True}
                    for item in still_missing
                ],
            }
            logger.warning(f"Still missing arguments after attempt {attempts}: {still_missing}")

        # Max attempts reached
        state.status = AgentStatus.ANALYZING
        self._reset_clarification(state)
        logger.error("Max clarification attempts reached. Some arguments are still missing.")
        logger.debug(f"Agents state after failing args clarification: {state}")

    def _apply_clarification_via_llm(self, state: OSAState, answers: dict):
        """
        Use LLM to fill missing arguments AFTER user clarification.
        This prevents re-running the full planning and only updates arguments.
        """
        if not state.missing_arguments:
            return

        parser = PydanticOutputParser(pydantic_object=ArgumentDetectionResponse)
        system_message = self._render("system_messages.fill_missing_system_message", safe=True)

        missing_fields_str = "\n".join(
            f"- Task: {item['task_id']}, field: {item['field']}, description: {item['prompt']}"
            for item in state.missing_arguments
        )

        answers_str = "\n".join(f"{k}: {v}" for k, v in answers.items())

        prompt = self._render(
            "osa_agent.fill_missing_after_clarification",
            missing=missing_fields_str,
            user_answers=answers_str,
        )
        logger.debug(f"Argument clarification prompt used: {prompt}")

        response = self._run_llm(prompt, parser, system_message)
        logger.debug(f"LLM clarification fill output: {response.root}")

        # Update tasks with the LLM-processed arguments
        for op_name, args in response.root.items():
            task = state.get_task(op_name)
            if not task:
                logger.warning(f"_apply_clarification_via_llm: unknown operation '{op_name}' in LLM output")
                continue

            if not isinstance(args, dict):
                logger.warning(f"_apply_clarification_via_llm: invalid args for '{op_name}': {args}")
                continue

            task.args.update(args)
            logger.info(f"Task '{task.id}' updated with clarified args: {task.args}")

    @staticmethod
    def _task_has_arg(state: OSAState, missing_item: dict) -> bool:
        """
        Check that a specific argument for a task is properly filled.
        Considers empty values as missing.

        missing_item = {"task_id": "...", "field": "...", "prompt": "..."}
        """
        task = state.get_task(missing_item["task_id"])
        if not task or not task.args or missing_item["field"] not in task.args:
            return False

        value = task.args[missing_item["field"]]
        # treat empty values as missing
        if value is None:
            return False
        if isinstance(value, (list, tuple, dict)) and len(value) == 0:
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        return True

    @staticmethod
    def _build_prompt_for_field(field: FieldInfo) -> str:
        """
        Build a descriptive prompt for a single argument based on its Pydantic FieldInfo.

        - Uses description if provided
        - Adds type instructions for List or Literal fields
        - Adds default info for clarity

        Args:
            field (FieldInfo): The Pydantic field info object.
        """
        desc = field.description or ""

        # Check if type is Literal → list allowed values
        origin = get_origin(field.annotation)
        if origin is Literal:
            allowed = get_args(field.annotation)
            desc += f" Allowed values: {list(allowed)}."

        # Check if type is list → indicate list expected
        elif origin in (list, List):
            desc += " Return as a list, even if only one element."

        # Optional: check if default exists
        if field.default is not None and field.default != Ellipsis:
            desc += f" Default: {field.default!r}."

        return desc
