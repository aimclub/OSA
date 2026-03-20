from langchain_core.output_parsers import PydanticOutputParser

from osa_tool.core.models.agent_status import AgentStatus
from osa_tool.osa_agent.agents.intent_router.models import IntentDecision
from osa_tool.osa_agent.base import BaseAgent
from osa_tool.osa_agent.state import OSAState
from osa_tool.ui.input_for_chat import wait_for_user_clarification
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import rich_section


class IntentRouterAgent(BaseAgent):
    """
    Agent responsible for detecting user intent and determining the appropriate scope of tasks to be executed.
    
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
        1. Handles user clarification if the system is waiting for input from this agent.
        2. Uses an LLM to detect the user's intent and task scope.
        3. Updates the state's status based on the LLM's confidence score.
        4. Decides whether to proceed with analysis or request user clarification.
        
        WHY: The agent determines the user's goal (e.g., documentation generation, code analysis) and ensures the request is sufficiently clear before advancing the workflow. Low‑confidence or ambiguous intents trigger a clarification loop to avoid incorrect downstream processing.
        
        Args:
            state: Current workflow state. If the state indicates this agent is waiting for user clarification, the method collects the user's clarified request and optional attachment before proceeding.
        
        Returns:
            Updated state with detected intent, task scope, confidence score, and a new status. The status is set to ANALYZING if the intent is clear (confidence ≥ 0.5 and intent not "unknown"); otherwise, it is set to WAITING_FOR_USER and clarification fields are populated in the state.
        """
        rich_section("Intent Router Agent")
        state.active_agent = self.name

        if state.status == AgentStatus.WAITING_FOR_USER and state.clarification_agent == self.name:
            answers = wait_for_user_clarification(state)
            state.active_request = answers.get("user_request")
            state.active_request_source = "user"

            if answers.get("attachment"):
                state.attachment = answers.get("attachment")

        parser = PydanticOutputParser(pydantic_object=IntentDecision)

        system_message = self._render("system_messages.intent_router", safe=True)

        prompt = self._render(
            "osa_agent.intent_router",
            active_request=state.active_request,
            attachment=state.attachment,
        )

        decision: IntentDecision = self._run_llm(prompt, parser, system_message)

        logger.info(
            "Intent decision: intent=%s, task_scope=%s, confidence=%s",
            decision.intent,
            decision.task_scope,
            decision.confidence,
        )

        state.intent = decision.intent
        state.task_scope = decision.task_scope
        state.intent_confidence = decision.confidence

        # Low confidence → wait for user clarification
        if decision.confidence < 0.5 or decision.intent == "unknown":
            logger.info("Low confidence or unknown intent; requesting user clarification")
            state.status = AgentStatus.WAITING_FOR_USER

            state.clarification_required = True
            state.clarification_agent = self.name
            state.clarification_type = "user_request"
            state.clarification_payload = {
                "question": "Your intent is unclear. Please refine your request.",
                "fields": [
                    {
                        "name": "user_request",
                        "prompt": "Clarified user request:",
                        "required": True,
                    },
                    {
                        "name": "attachment",
                        "prompt": "Attachment (optional):",
                        "required": False,
                    },
                ],
            }
        else:
            logger.debug("Intent accepted; proceeding to repo analysis")
            state.status = AgentStatus.ANALYZING
            self._reset_clarification(state)

        state.session_memory.append(
            {
                "agent": self.name,
                "active_request": state.active_request,
                "attachment": bool(state.attachment),
                "intent": decision.intent,
                "task_scope": decision.task_scope,
                "confidence": decision.confidence,
                "new_status": state.status,
                "prompt": prompt,
            }
        )
        logger.debug("State after intent_router: %s", state)
        logger.info("Intent router completed; status=%s", state.status)

        return state
