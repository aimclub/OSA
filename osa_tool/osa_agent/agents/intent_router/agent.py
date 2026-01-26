from langchain_core.output_parsers import PydanticOutputParser

from osa_tool.core.models.agent import AgentStatus
from osa_tool.osa_agent.agents.intent_router.models import IntentDecision
from osa_tool.osa_agent.base import BaseAgent
from osa_tool.osa_agent.state import OSAState
from osa_tool.ui.input_for_chat import clarify_user_input
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.utils import rich_section


class IntentRouterAgent(BaseAgent):
    """
    Agent responsible for intent and task scope detection.

    The IntentRouterAgent:
    - determines the user's intent and task scope using an LLM
    - requests clarification if the intent confidence is low
    - updates the workflow state accordingly
    """

    name = "IntentRouter"

    def run(self, state: OSAState) -> OSAState:
        """
        Route the user's request to the appropriate workflow path.

        This method:
        1. Handles user clarification if the system is waiting for input
        2. Uses an LLM to detect intent and task scope
        3. Updates state status based on confidence score
        4. Decides whether to continue analysis or wait for user input

        Args:
            state (OSAState): Current workflow state.

        Returns:
            OSAState: Updated state with detected intent and routing status.
        """
        rich_section("Intent Router Agent")

        if state.status == AgentStatus.WAITING_FOR_USER:
            clarification = clarify_user_input()
            state.user_request = clarification.user_request

            if clarification.attachment:
                state.attachment = clarification.attachment

        parser = PydanticOutputParser(pydantic_object=IntentDecision)

        system_message = PromptBuilder.render(
            self.context.prompts.get("system_messages.intent_router"),
            safe=True,
        )

        prompt = PromptBuilder.render(
            self.context.prompts.get("osa_agent.intent_router"),
            user_request=state.user_request,
            attachment=state.attachment,
        )

        decision: IntentDecision = self.context.get_model_handler("general").run_chain(
            prompt=prompt,
            parser=parser,
            system_message=system_message,
        )

        logger.info(f"Intent decision: {decision.intent}, {decision.task_scope}")

        state.intent = decision.intent
        state.task_scope = decision.task_scope
        state.intent_confidence = decision.confidence

        # Low confidence → wait for user clarification
        state.status = (
            AgentStatus.WAITING_FOR_USER
            if decision.confidence < 0.5 or decision.intent == "unknown"
            else AgentStatus.ANALYZING
        )

        logger.info(f"Updated state after intent_router: {state.status}")

        state.active_agent = self.name
        return state
