from typing import Any, Dict, List, Optional

from osa_tool.osa_agent.config import ToolSpec
from osa_tool.osa_agent.state import OSAAgentState
from osa_tool.utils.prompts_builder import PromptLoader, PromptBuilder


class OSAPlannerNode:
    """
    Node responsible for generating execution plans based on the user input.
    Uses a LLM model and tool descriptions to create step-by-step plans.
    """

    def __init__(self, llm: Any, tools_description: List[ToolSpec], prompts: PromptLoader, max_retries: int = 1):
        self.llm = llm
        self.tools_description = tools_description
        self.prompts = prompts
        self.max_retries = max_retries

    def __call__(self, state: OSAAgentState, config: Optional[Dict] = None) -> OSAAgentState:
        """
        Generate a plan based on the state.input and optionally attached image.
        Updates state.plan with list of steps.
        """
        # Gather input
        user_input = state.input
        last_memory = state.last_memory
        attached_img = state.attachment

        # Render tools description
        tools_rendered = ", ".join([t.description for t in self.tools_description])

        # Build prompt
        prompt = PromptBuilder.render(
            self.prompts.get("osa_agent.planner"),
            tools_rendered=tools_rendered,
            last_memory=last_memory,
            additional_hints=self.prompts.additional_hints,
            problem_statement=self.prompts.problem_statement,
            rules=self.prompts.rules,
            examples=self.prompts.examples,
            desc_restrictions=self.prompts.desc_restrictions,
            image_description=attached_img,
        )

        # Call LLM and handle retries
        plan_steps: List[List[str]] = []
        for attempt in range(self.max_retries):
            try:
                llm_response = self.llm.invoke(prompt)
                # Here we assume response has a .content attribute
                plan_steps = self.parse_plan(llm_response.content)
                state.plan = plan_steps
                return state
            except Exception as e:
                print(f"Planner attempt {attempt+1} failed: {e}")

        # fallback if all retries fail
        state.plan = []
        return state

    @staticmethod
    def parse_plan(raw_output: str) -> List[List[str]]:
        """Parse raw LLM output into structured plan steps."""
        try:
            import json

            parsed = json.loads(raw_output)
            return parsed.get("steps", [])
        except Exception:
            # fallback: wrap raw text into one step
            return [[raw_output]]
