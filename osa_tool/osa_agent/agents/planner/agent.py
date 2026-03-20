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
    Agent responsible for planning and orchestrating the execution workflow for repository analysis and enhancement tasks.
    
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
        
        This method orchestrates the creation of an execution plan by selecting and ordering operations, detecting required arguments, and preparing the workflow for execution. It also handles re-planning after a reviewer request and manages interactive clarification when user input is needed for missing arguments.
        
        The planning process follows these steps:
        1. Registers all available operations.
        2. Retrieves operations applicable to the current state.
        3. Uses an LLM to decide which operations to run.
        4. Builds an ordered task plan from the selected operations.
        5. Detects and assigns additional arguments via LLM inference for operations that require it.
        6. Fills default arguments for operations with an 'auto' argument policy.
        7. Checks for any remaining missing required arguments that require user clarification.
        8. Updates the workflow state and session memory with the plan and planning metadata.
        
        If the workflow status is WAITING_FOR_USER and this agent is designated to handle clarification, the method enters a clarification loop to collect missing arguments from the user before proceeding.
        
        Args:
            state: Current workflow state. The state's plan_history is maintained when re-planning after a reviewer request; otherwise, it is cleared for a new request.
        
        Returns:
            Updated state containing the execution plan, plan reasoning, current step index, and updated status. If missing arguments are detected and require user clarification, the returned state will have status WAITING_FOR_USER and contain a clarification payload.
        """
        rich_section("Planner Agent")
        state.active_agent = self.name

        if state.status == AgentStatus.WAITING_FOR_USER and state.clarification_agent == self.name:
            logger.info("Planner handling missing argument clarification (loop)")
            self._clarification_loop(state)
            return state

        state.status = AgentStatus.ANALYZING
        logger.info("Planner started")
        register_all_operations()

        # Maintain plan history when re-planning after review: append last plan or clear for new request
        if state.active_request_source == "reviewer" and state.plan:
            state.plan_history = list(state.plan_history) + [[t.model_dump() for t in state.plan]]
            logger.debug("Appended current plan to plan_history (%s prior plans)", len(state.plan_history))
        else:
            state.plan_history = []
            logger.debug("Cleared plan_history (new request or first plan)")

        available_ops = self._get_available_operations(state)
        logger.debug("Available operations: %s", [op.name for op in available_ops])

        decision = self._make_decision(state, available_ops)
        state.plan_reasoning = (decision.reasoning or "").strip()
        selected_ops = self._select_operations(decision)
        logger.info("LLM selected operations: %s", [op.name for op in selected_ops])

        self._build_execution_plan(state, selected_ops)
        logger.debug("Initial plan tasks: %s", [t.id for t in state.plan])

        detect_args_prompt = self._detect_additional_arguments(state)
        logger.debug("Argument detection prompt used: %s", detect_args_prompt)

        self._fill_default_args(state)
        args_summary = "\n".join("%s: %s" % (task.id, task.args) for task in state.plan)
        logger.debug("Task args after filling defaults:\n%s", args_summary)

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
        logger.debug("Session memory updated with Planner step")
        logger.debug("State after planning: %s", state)
        logger.info("Planner completed: %s tasks", len(state.plan))

        return state

    @staticmethod
    def _get_available_operations(state: OSAState) -> List[Operation]:
        """
        Retrieve all operations applicable to the current state.
        
        This method queries the operation registry to obtain a filtered list of operations that can be executed given the current workflow state. It delegates the applicability check to the registry, which evaluates each operation's specific constraints (such as intent and scope) against the state.
        
        Args:
            state: Current workflow state.
        
        Returns:
            List of Operation instances that can run in this state.
        """
        return OperationRegistry.applicable(state)

    @staticmethod
    def _format_plan_history_section(plan_history: List[List[dict]]) -> str:
        """
        Format plan_history for the planner prompt so the LLM sees which plans were already tried.
        Returns an empty string when there is no history.
        
        This method is used to provide the planner agent with context about previously attempted task plans
        that were not approved, helping to avoid redundant or unsuccessful planning cycles.
        
        Args:
            plan_history: A list of plans, where each plan is a list of task dictionaries.
                          Each task dictionary should contain an "id" key to identify the task.
        
        Returns:
            A formatted string summarizing the plan history, prefixed with a header.
            If plan_history is empty, returns an empty string.
            The output lists each plan cycle by number and the IDs of the tasks it contained.
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
        
                This method constructs a prompt from the current workflow state and available operations, then queries the LLM to produce a structured decision. It provides the LLM with context about the active request, intent, task scope, repository data, plan history (to avoid redundant attempts), and a formatted list of available operations.
        
                Args:
                    state: Current workflow state, containing the active request, intent, task scope, plan history, and repository data.
                    available_ops: Operations applicable to the current state, each with a name and description.
        
                Returns:
                    Model output describing selected operations, parsed and validated as a PlannerDecision.
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
        logger.debug("Planner _make_decision prompt: %s ", prompt)
        return self._run_llm(prompt, parser, system_message)

    @staticmethod
    def _select_operations(decision: PlannerDecision) -> List[Operation]:
        """
        Resolve and sort selected operations based on priority.
        
        This method converts operation names from a planner decision into actual operation objects, filters out any names not found in the registry, and sorts the resulting list by each operation's priority attribute. This ensures that operations are executed in the correct order as determined by their defined priorities.
        
        Args:
            decision: Planner decision containing a list of operation names to be resolved.
        
        Returns:
            Sorted list of operation descriptors, ordered from highest to lowest priority (assuming lower priority numbers indicate higher priority, as is typical with sorting in ascending order).
        """
        ops = [OperationRegistry.get(name) for name in decision.operations if OperationRegistry.get(name)]
        ops.sort(key=lambda op: op.priority)
        return ops

    def _build_execution_plan(self, state: OSAState, operations: List[Operation]) -> None:
        """
        Build the task execution plan from selected operations.
        
        This method also tracks operations that require additional arguments
        for later argument detection.
        
        WHY: The method constructs a sequential plan of tasks from the selected operations,
        ensuring that each operation's tasks are added to the overall workflow plan.
        It simultaneously identifies operations that have an argument schema, so that
        missing arguments for those operations can be detected and filled in a later step.
        
        Args:
            state: Current workflow state. The plan attribute of this state will be
                   populated with the tasks generated from the operations.
            operations: Selected operations to be executed. Each operation contributes
                        one or more tasks to the plan via its plan_tasks method.
        
        Returns:
            None. The method modifies the state.plan in-place and updates the internal
            list self._operations_with_args.
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
        
        Uses an LLM to infer missing or optional arguments based on the user's request and operation prompts. This step is performed only for operations that have been flagged as requiring argument detection (stored in `self._operations_with_args`). WHY: Some operations have arguments that are not explicitly provided in the initial user request; this method uses the LLM to intelligently fill in those gaps based on contextual prompts and field definitions.
        
        Args:
            state: Current workflow state containing the active request and plan tasks.
        
        Returns:
            The prompt string used for argument detection, primarily for debugging and traceability. Returns an empty string if no operations require argument detection.
        
        Behavior:
        - If `self._operations_with_args` is empty, returns immediately without calling the LLM.
        - Constructs a system message and a detailed prompt listing each operation and its argument fields, where each field description is built using `_build_prompt_for_field`.
        - Sends the prompt to the LLM via `_run_llm` with a Pydantic parser to obtain a structured response.
        - Iterates over the LLM's response, updating the arguments of the corresponding tasks in the state's plan.
        - Logs warnings for operations not found in the state or for malformed argument data.
        - Logs debug information about the LLM output and updated task arguments.
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
        logger.debug("_detect_additional_arguments LLM output: %s", response.root)

        for op_name, args in response.root.items():
            task = state.get_task(op_name)
            if not task:
                logger.warning("_detect_additional_arguments: unknown operation '%s' in LLM output", op_name)
                continue

            if not isinstance(args, dict):
                logger.warning("_detect_additional_arguments: invalid args for '%s': %s", op_name, args)
                continue

            task.args.update(args)
            logger.debug("_detect_additional_arguments -> task '%s' updated args: '%s'", task.id, task.args)

        return prompt

    def _fill_default_args(self, state: OSAState) -> None:
        """
        Sets default argument values for operations if LLM returns nothing and args_policy == 'auto'.
        
        Why:
            When the LLM does not provide arguments for certain operations, this method ensures that tasks are populated with default values as defined by the operation's schema, preventing incomplete task execution.
        
        Args:
            state: The OSAState containing the plan and tasks to be updated.
        
        Note:
            Only operations where args_policy is explicitly 'auto' and the corresponding task currently lacks arguments are affected. If an operation is not in self._operations_with_args or its task already has arguments, no changes are made.
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
                logger.debug("_fill_default_args -> task '%s' field '%s' set to default: %s", task.id, k, v)

    def _check_missing_args(self, state: OSAState) -> bool:
        """
        Checks whether there are any unfilled required arguments with args_policy == 'ask_if_missing'.
        Prepares state for multi-question clarification via LLM.
        
        WHY: When an operation's argument policy is 'ask_if_missing', the system must prompt the user for any required arguments that were not provided. This method identifies those missing arguments and structures them into a clarification payload so the LLM or UI can ask the user for them collectively.
        
        Args:
            state: The current OSAState containing the plan and tasks.
        
        Returns:
            True if clarification is required from the user (i.e., missing required arguments were found); False otherwise.
        
        Behavior:
            - Iterates over operations registered with the agent that have an args_policy of 'ask_if_missing'.
            - For each such operation, checks the corresponding task in the state to see if all required arguments (as defined by the operation's schema) have been provided.
            - If a required argument is missing, builds a prompt for that argument using the field's description and constraints.
            - Collects all missing arguments across operations and stores them in state.missing_arguments.
            - Sets state.clarification_required to True and prepares a clarification payload with a consolidated list of fields (each field is identified by task_id::field_name) and their prompts.
            - Updates the state status to WAITING_FOR_USER and logs the missing fields.
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
                logger.debug("_task_with_unfilled_required_args: '%s'", missing[-1])

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
        missing_fields = [item["field"] for item in missing]
        logger.warning("Missing required arguments: %s", missing_fields)
        logger.debug("State after detecting missing arguments: %s", state)

        return True

    def _clarification_loop(self, state: OSAState) -> None:
        """
        Loop to handle missing arguments clarification from the user.
        Uses the LLM to validate and convert the user's answers into proper task arguments.
        Stops when all missing arguments are filled or the maximum number of clarification attempts is reached.
        
        WHY: This loop manages an interactive clarification process, ensuring that the agent can collect necessary information from the user to complete its tasks without re-running the entire planning pipeline. It iteratively requests user input, processes the responses via the LLM to update task arguments, and checks for completion.
        
        Process:
        1. For each attempt up to the maximum allowed (state.clarification_attempts), prompt the user for the missing arguments.
        2. Use the LLM to interpret the user's answers and update the corresponding task arguments in the state.
        3. After each attempt, check which arguments remain missing.
        4. If all arguments are filled, reset the clarification state, update the agent status to ANALYZING, and exit.
        5. If arguments are still missing, update the state with the remaining missing arguments and a new clarification payload for the next attempt.
        6. When the maximum attempts are reached without filling all arguments, reset the clarification state, set the status to ANALYZING, and log an error.
        
        Args:
            state: The current OSAState containing the plan, tasks, missing arguments, and clarification configuration.
        
        Note:
            The method modifies the provided state in place, updating missing_arguments, clarification_payload, and status as the loop progresses.
        """

        attempts = 0
        while attempts < state.clarification_attempts:
            attempts += 1
            logger.info("Clarification attempt %s of %s", attempts, state.clarification_attempts)

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
                logger.info("All missing arguments filled successfully")
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
            logger.warning("Still missing arguments after attempt %s: %s", attempts, still_missing)

        # Max attempts reached
        state.status = AgentStatus.ANALYZING
        self._reset_clarification(state)
        logger.error("Max clarification attempts reached; some arguments still missing")
        logger.debug("State after failing args clarification: %s", state)

    def _apply_clarification_via_llm(self, state: OSAState, answers: dict) -> None:
        """
        Use LLM to fill missing arguments AFTER user clarification.
        This prevents re-running the full planning and only updates arguments.
        
        WHY: When the user provides clarification answers for previously missing arguments, this method efficiently applies those answers only to the affected tasks, avoiding the cost and potential inconsistency of re-executing the entire planning pipeline.
        
        Args:
            state: The current OSAState containing the plan and its tasks with missing arguments.
            answers: A dictionary mapping user-provided clarification question identifiers to their answers.
        
        Process:
        1. If no arguments are missing, returns immediately.
        2. Constructs a prompt for the LLM that lists all missing argument fields (by task and description) and the user's clarification answers.
        3. Calls the LLM with this prompt and a parser expecting a structured response mapping operation names to argument dictionaries.
        4. For each operation in the LLM response, finds the corresponding task in the state and updates its arguments with the LLM-processed values.
        5. Logs updates and warnings for operations not found or with invalid argument formats.
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
        logger.debug("Argument clarification prompt: %s", prompt)

        response = self._run_llm(prompt, parser, system_message)
        logger.debug("LLM clarification fill output: %s", response.root)

        # Update tasks with the LLM-processed arguments
        for op_name, args in response.root.items():
            task = state.get_task(op_name)
            if not task:
                logger.warning("_apply_clarification_via_llm: unknown operation '%s' in LLM output", op_name)
                continue

            if not isinstance(args, dict):
                logger.warning("_apply_clarification_via_llm: invalid args for '%s': %s", op_name, args)
                continue

            task.args.update(args)
            logger.info("Task '%s' updated with clarified args: %s", task.id, task.args)

    @staticmethod
    def _task_has_arg(state: OSAState, missing_item: dict) -> bool:
        """
        Check that a specific argument for a task is properly filled.
        Considers empty values (None, empty collections, or blank strings) as missing.
        
        Args:
            state: The current state containing the plan and tasks.
            missing_item: A dictionary with keys "task_id", "field", and "prompt". It identifies which task and argument to validate.
        
        Returns:
            True if the argument exists and has a non‑empty value; False otherwise.
        
        Why:
            This validation ensures that required task arguments are present and meaningful before proceeding with further operations, preventing errors from missing or empty inputs.
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
        
        - Uses the field's description if provided.
        - For Literal fields, appends the list of allowed values.
        - For List fields, adds an instruction to return as a list, even with a single element.
        - If a default value exists (and is not Ellipsis), appends the default for clarity.
        
        Args:
            field: The Pydantic field info object containing annotation, description, and default.
        
        Returns:
            A single string describing the argument, suitable for use in prompts or UI displays.
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
