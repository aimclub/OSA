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
        """
        Ask the user to approve or reject the result, then optionally analyze feedback.
        
        If the user approves, state.approval is set to True and the graph routes to the finalizer.
        If the user rejects, the method collects detailed feedback, uses an LLM to extract intent or scope changes, and routes the state back to the planner for another iteration.
        
        The method also enforces a maximum number of review cycles; if exceeded, approval is forced and the state is routed to the finalizer.
        
        Args:
            state: The current workflow state. The method updates this state in place based on user input and analysis.
        
        Returns:
            The updated state after processing user approval or feedback.
        
        Why:
        - The reviewer agent acts as a gatekeeper before finalizing the workflow, ensuring the user validates the output.
        - When feedback is provided, an LLM analyzes it to determine whether the user's request constitutes a new intent or a change in task scope, allowing the system to adapt the workflow accordingly.
        - The review cycle limit prevents infinite loops in the planning–execution–review cycle.
        """
        rich_section("Reviewer Agent")
        state.active_agent = self.name
        logger.debug("Reviewer started; waiting for user approval")

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
        logger.debug("User approval answer: '%s'", approval_answer)

        if approval_answer in {"yes", "y"}:
            state.approval = True
            self._reset_clarification(state)
            state.status = AgentStatus.ANALYZING
            logger.info("User approved the result; routing to Finalizer")
            return state

        state.approval = False
        logger.info("User requested changes; collecting feedback")
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
        logger.debug("User feedback: %s", feedback_text)

        logger.info("Analyzing feedback with LLM")
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
                "Max review cycles reached (%s/%s); routing to finalizer",
                state.review_cycle_count,
                state.max_review_cycles,
            )

        logger.debug("State after reviewer: %s", state)
        return state

    def _analyze_feedback_with_llm(self, state: OSAState, feedback_text: str) -> ReviewerDecision:
        """
        Send feedback text to the LLM to produce a ReviewerDecision, which determines whether the user's feedback indicates a new intent or task scope.
        
        This method constructs a prompt using the current state and the provided feedback, queries the LLM, and parses the response into a structured decision. It logs both the prompt sent to the LLM and the resulting decision for debugging.
        
        Args:
            state: The current OSAState, containing the intent and task_scope to provide context for the LLM.
            feedback_text: User feedback text to be analyzed.
        
        Returns:
            ReviewerDecision: Parsed LLM decision about whether the feedback introduces a new intent or task_scope.
        """
        parser = PydanticOutputParser(pydantic_object=ReviewerDecision)

        system_message = self._render("system_messages.reviewer", safe=True)

        prompt = self._render(
            "osa_agent.reviewer_user_prompt",
            feedback_text=feedback_text,
            current_intent=state.intent,
            current_task_scope=state.task_scope,
        )
        logger.debug("Reviewer LLM prompt: %s", prompt)

        decision: ReviewerDecision = self._run_llm(prompt, parser, system_message)
        logger.debug("ReviewerDecision: %s", decision)
        return decision

    def _apply_decision(self, state: OSAState, decision: ReviewerDecision) -> OSAState:
        """
        Update the OSAState based on the ReviewerDecision.
        
        This method applies the reviewer's analysis to modify the workflow state. It updates intent and task scope if the reviewer indicates they are insufficient or incorrect, logs changes, and prepares the state for the next planning phase by resetting any ongoing clarification context and setting the status to ANALYZING.
        
        Args:
            state: Current workflow state.
            decision: Output of LLM analysis, containing flags and optional new values for intent and task scope.
        
        Returns:
            Updated workflow state ready for Planner.
        
        The method performs the following updates:
        - Sets review_requires_new_intent and review_requires_new_task_scope from the decision.
        - If a new intent is required and provided, updates state.intent (and optionally state.task_scope) and logs the change.
        - If only a new task scope is required and provided, updates state.task_scope and logs the change.
        - Stores the reviewer_summary from the decision.
        - Changes the state status to ANALYZING and resets clarification-related fields to clear any previous clarification context.
        """
        state.review_requires_new_intent = decision.requires_new_intent
        state.review_requires_new_task_scope = decision.requires_new_task_scope

        if decision.requires_new_intent and decision.new_intent:
            state.intent = decision.new_intent
            if decision.new_task_scope is not None:
                state.task_scope = decision.new_task_scope
            logger.info("Reviewer set new intent: %s, scope=%s", state.intent, state.task_scope)
        elif decision.requires_new_task_scope and decision.new_task_scope is not None:
            state.task_scope = decision.new_task_scope
            logger.info("Reviewer updated task_scope: %s", state.task_scope)

        state.reviewer_summary = decision.reviewer_summary

        state.status = AgentStatus.ANALYZING
        self._reset_clarification(state)
        return state
