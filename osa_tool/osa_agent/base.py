from abc import ABC, abstractmethod
from typing import Any, ClassVar, Optional

from langchain_core.output_parsers import PydanticOutputParser

from osa_tool.osa_agent.context import AgentContext
from osa_tool.osa_agent.state import OSAState
from osa_tool.utils.prompts_builder import PromptBuilder


class BaseAgent(ABC):
    """
    Base abstract class for all agents in the OSA workflow.

    Each agent represents a single step in the overall pipeline
    (e.g. intent routing, planning, execution, review, finalization)
    and operates on a shared AgentContext and mutable OSAState.
    """

    name: ClassVar[str]

    def __init__(self, context: AgentContext) -> None:
        """
        Initialize the agent with a shared execution context.

        Args:
            context: Shared context containing configuration,
                repository metadata, model handlers, and workflow utilities.
        """
        self.context: AgentContext = context

    @abstractmethod
    def run(self, state: OSAState) -> OSAState:
        """
        Execute the agent's logic and return an updated state.

        Args:
            state: Current workflow state.

        Returns:
            Updated workflow state after agent execution.
        """
        ...

    def _render(self, template_key: str, **kwargs: Any) -> str:
        """
        Render a prompt template from the context prompts registry.

        Args:
            template_key: Key used to look up the template in context.prompts.
            **kwargs: Variables to pass into the template.

        Returns:
            Rendered prompt string.
        """
        return PromptBuilder.render(self.context.prompts.get(template_key), **kwargs)

    def _run_llm(
        self,
        prompt: str,
        parser: PydanticOutputParser,
        system_message: Optional[str] = None,
    ) -> Any:
        """
        Run the general model handler with the given prompt and parser.

        Args:
            prompt: User or task-specific prompt text.
            parser: Pydantic output parser to parse the LLM response.
            system_message: Optional system message for the LLM.

        Returns:
            Parsed output from the LLM (type depends on the parser's target model).
        """
        return self.context.get_model_handler("general").run_chain(
            prompt=prompt,
            parser=parser,
            system_message=system_message,
        )

    @staticmethod
    def _reset_clarification(state: OSAState) -> None:
        """
        Reset all clarification-related fields in the given state to their default values,
        except for clarification_attempts.
        """
        state.clarification_required = False
        state.clarification_agent = None
        state.clarification_type = "single_question"
        state.clarification_payload = None
        state.clarification_answer = None
