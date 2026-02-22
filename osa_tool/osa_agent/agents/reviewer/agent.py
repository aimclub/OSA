from langchain_core.output_parsers import PydanticOutputParser

from osa_tool.core.models.agent_status import AgentStatus
from osa_tool.osa_agent.agents.reviewer.models import ReviewerDecision
from osa_tool.osa_agent.base import BaseAgent
from osa_tool.osa_agent.state import OSAState
from osa_tool.ui.input_for_chat import wait_for_user_clarification
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import rich_section


class ReviewerAgent(BaseAgent):
    """
    ReviewerAgent validates the execution results and user feedback,
    determines whether:
      - the task is completed,
      - user needs changes,
      - user wants a completely new intent or task scope.
    """

    name = "Reviewer"

    def run(self, state: OSAState) -> OSAState:
        rich_section("Reviewer Agent")
        state.active_agent = self.name

        state.status = AgentStatus.WAITING_FOR_USER

        state.clarification_required = True
        state.clarification_agent = self.name
        state.clarification_type = "review"
        state.clarification_payload = {
            "question": "Please review the latest result.",
            "fields": [
                {
                    "name": "accept",
                    "prompt": "Do you approve the result? (yes/no):",
                    "required": True,
                }
            ],
        }

        answers = wait_for_user_clarification(state)
        approval_answer = answers.get("accept", "").strip().lower()
        logger.debug(f"User approval answer: '{approval_answer}'")

        if approval_answer in {"yes", "y"}:
            state.approval = True
            self._reset_clarification(state)
            state.status = AgentStatus.ANALYZING
            logger.info("User approved the result. Moving to Finalizer.")
            return state

        state.approval = False
        state.clarification_payload = {
            "question": "Please describe what needs to be improved.",
            "fields": [
                {
                    "name": "feedback",
                    "prompt": "What changes are required? (describe in detail):",
                    "required": True,
                }
            ],
        }

        feedback_answers = wait_for_user_clarification(state)
        feedback_text = feedback_answers.get("feedback", "").strip()
        logger.debug(f"User feedback text: '{feedback_text}'")

        logger.info("Received user feedback. Passing it to LLM ReviewerDecision.")
        state.review_feedback = feedback_text
        decision = self._analyze_feedback_with_llm(state, feedback_text)

        self._apply_decision(state, decision)

        # Drive next planning cycle from feedback
        state.active_request = feedback_text
        state.active_request_source = "reviewer"

        # Enforce max review cycles for Planner -> Executor -> Reviewer loop
        state.review_cycle_count = state.review_cycle_count + 1
        if state.review_cycle_count >= state.max_review_cycles:
            self._reset_clarification(state)
            state.review_cycles_exhausted = True
            state.approval = True
            logger.warning(
                f"Max review cycles reached ({state.review_cycle_count}/{state.max_review_cycles}). Routing to finalizer."
            )

        logger.debug(state)
        return state

    def _analyze_feedback_with_llm(self, state: OSAState, feedback_text: str) -> ReviewerDecision:
        """
        Send feedback text to LLM to produce a ReviewerDecision.

        Args:
            feedback_text (str): User feedback.

        Returns:
            ReviewerDecision: Parsed LLM decision about new intent/task_scope.
        """
        parser = PydanticOutputParser(pydantic_object=ReviewerDecision)

        system_message = self._render("system_messages.reviewer", safe=True)

        prompt = self._render(
            "osa_agent.reviewer_user_prompt",
            feedback_text=feedback_text,
            current_intent=state.intent,
            current_task_scope=state.task_scope,
        )
        logger.debug(f"Reviewer LLM prompt:\n{prompt}")

        logger.info("Running Reviewer LLM decision parser...")
        decision: ReviewerDecision = self._run_llm(prompt, parser, system_message)
        logger.debug(f"ReviewerDecision received: {decision}")
        return decision

    def _apply_decision(self, state: OSAState, decision: ReviewerDecision) -> OSAState:
        """
        Update the OSAState based on the ReviewerDecision.

        Args:
            state (OSAState): Current workflow state.
            decision (ReviewerDecision): Output of LLM analysis.

        Returns:
            OSAState: Updated workflow state ready for Planner.
        """
        state.review_requires_new_intent = decision.requires_new_intent
        state.review_requires_new_task_scope = decision.requires_new_task_scope

        if decision.requires_new_intent and decision.new_intent:
            state.intent = decision.new_intent
            if decision.new_task_scope is not None:
                state.task_scope = decision.new_task_scope
            logger.info(f"Reviewer set NEW INTENT: {state.intent}, scope={state.task_scope}")
        elif decision.requires_new_task_scope and decision.new_task_scope is not None:
            state.task_scope = decision.new_task_scope
            logger.info(f"Reviewer UPDATED task_scope: {state.task_scope}")

        state.reviewer_summary = decision.reviewer_summary

        state.status = AgentStatus.ANALYZING
        self._reset_clarification(state)
        return state
