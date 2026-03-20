from abc import ABC, abstractmethod
from typing import Any, ClassVar, Optional

from langchain_core.output_parsers import PydanticOutputParser

from osa_tool.osa_agent.context import AgentContext
from osa_tool.osa_agent.state import OSAState
from osa_tool.utils.prompts_builder import PromptBuilder


class BaseAgent(ABC):
    """
    Base abstract class defining the core interface and structure for all specialized agents within the automated analysis and enhancement workflow.
    
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
                This context provides all necessary dependencies and state
                required for the agent to perform its tasks within the OSA Tool
                pipeline, ensuring consistent access to resources and configurations
                across different operations.
        
        Why:
            Using a shared AgentContext allows all agents in the system to operate
            with a unified configuration and set of utilities, promoting consistency
            and reducing redundancy. It centralizes access to essential components
            like the LLM handlers, repository data, and workflow tools, which are
            critical for the automated documentation and enhancement processes.
        """
        self.context: AgentContext = context

    @abstractmethod
    def run(self, state: OSAState) -> OSAState:
        """
        Execute the agent's logic and return an updated state.
        
        This is an abstract method that must be implemented by concrete agent subclasses.
        Each agent performs a specific, specialized operation (e.g., documentation generation,
        validation, or repository enhancement) as part of the larger OSA Tool workflow.
        
        Args:
            state: The current workflow state (OSAState), containing all data and context
                   needed for the agent's operation.
        
        Returns:
            The updated workflow state (OSAState) after the agent has executed its logic.
            The returned state should reflect any modifications, additions, or analyses
            performed by the agent.
        """
        ...

    def _render(self, template_key: str, **kwargs: Any) -> str:
        """
        Render a prompt template from the context prompts registry.
        
        The method looks up a template by its key in the agent's context and renders it with the provided variables. This centralizes prompt management and ensures consistent formatting across the agent's operations.
        
        Args:
            template_key: Key used to look up the template in context.prompts.
            **kwargs: Variables to pass into the template for rendering.
        
        Returns:
            Rendered prompt string.
        
        Raises:
            PromptBuilderError: If a placeholder key is missing from kwargs or if any other formatting error occurs during rendering.
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
        
        This method delegates to the "general" task-specific model handler to execute a synchronous LLM chain. The chain processes the prompt, optional system message, and parser to produce a validated, structured output. WHY: It provides a simplified interface for the agent to invoke the general-purpose LLM pipeline with built-in error handling and retries.
        
        Args:
            prompt: User or task-specific prompt text.
            parser: Pydantic output parser to parse and validate the LLM response.
            system_message: Optional system message for the LLM. If not provided, the handler's default system prompt is used.
        
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
        Reset all clarification-related fields in the given state to their default values, except for clarification_attempts.
        
        This is used to clear any ongoing clarification context (like questions, answers, or agent assignments) without resetting the attempt counter, allowing the agent to start a new clarification interaction while preserving the number of attempts already made.
        
        Args:
            state: The OSAState object whose clarification fields will be reset.
        
        The following fields are reset to their defaults:
        - clarification_required: Set to False.
        - clarification_agent: Set to None.
        - clarification_type: Set to "single_question".
        - clarification_payload: Set to None.
        - clarification_answer: Set to None.
        """
        state.clarification_required = False
        state.clarification_agent = None
        state.clarification_type = "single_question"
        state.clarification_payload = None
        state.clarification_answer = None
