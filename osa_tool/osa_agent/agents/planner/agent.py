from langchain_core.output_parsers import PydanticOutputParser

from osa_tool.core.models.agent import AgentStatus
from osa_tool.operations.registry import OperationRegistry
from osa_tool.osa_agent.agents.planner.models import PlannerDecision, ArgumentDetectionResponse
from osa_tool.osa_agent.base import BaseAgent
from osa_tool.osa_agent.state import OSAState
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.utils import rich_section


class PlannerAgent(BaseAgent):
    name = "Planner"

    def run(self, state: OSAState) -> OSAState:
        rich_section("Planner Agent")

        available_ops = OperationRegistry.applicable(state)

        decision = self._plan(state, available_ops)
        selected_ops = self._select_operations(decision)

        self._build_plan(state, selected_ops)
        detect_args_prompt = self._detect_additional_arguments(state, selected_ops)

        state.current_step_index = 0
        state.status = AgentStatus.GENERATING
        state.active_agent = self.name

        state.session_memory.append(
            {
                "agent": self.name,
                "decision": decision.model_dump(),
                "plan": [t.model_dump() for t in state.plan],
                "detect_args_prompt": detect_args_prompt,
            }
        )

        return state

    def _plan(self, state: OSAState, available_ops):
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
    def _select_operations(decision: PlannerDecision):
        ops = [OperationRegistry.get(name) for name in decision.operations if OperationRegistry.get(name)]
        ops.sort(key=lambda op: op.priority)
        return ops

    def _build_plan(self, state: OSAState, operations):
        state.plan = []
        self._operations_with_args = []

        for op in operations:
            tasks = op.plan_tasks()
            if op.args_schema:
                self._operations_with_args.append(op)
            state.plan.extend(tasks)

    def _detect_additional_arguments(self, state: OSAState, operations):
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
