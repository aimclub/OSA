import json

from pydantic import ValidationError

from osa_tool.osa_agent.planner.models import PlannerResponse
from osa_tool.osa_agent.planner.prompts import build_parameter_list
from osa_tool.osa_agent.state import AgentState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptLoader, PromptBuilder


class PlannerNode:
    def __init__(self, llm_model: str = "gpt-4", temperature: float = 0.0):
        self.llm = ChatOpenAI(model_name=llm_model, temperature=temperature)
        self.prompts = PromptLoader()

    def run(self, state: AgentState) -> PlannerResponse:
        """
        Runs PlannerNode for a given AgentState.
        Uses the LLM to infer parameters based on user_input and context.
        """
        parameter_list = build_parameter_list()

        user_input_payload = {
            "repo_url": state.user_input.repo_url,
            "user_request": state.user_input.user_request,
            "attachment": state.user_input.attachment,
            "current_parameters": state.parameters,
            "context": state.context,
        }

        prompt_template = self.prompts.get("osa_agent.planner_prompt")
        prompt = PromptBuilder.render(
            prompt_template, parameter_list=parameter_list, input=json.dumps(user_input_payload, indent=2)
        )

        llm_output = self.llm([{"role": "system", "content": prompt}])
        llm_text = llm_output[0].content.strip()

        try:
            response_dict = json.loads(llm_text)
        except json.JSONDecodeError as e:
            logger.error(f"PlannerNode: Failed to parse LLM output as JSON: {e}")
            raise ValueError(f"Invalid JSON from LLM: {llm_text}")

        try:
            response = PlannerResponse.model_validate(response_dict)
        except ValidationError as e:
            logger.error(f"PlannerNode: Response validation error: {e}")
            raise

        state.last_planner_output = response
        if response.action == "update_parameters":
            for param in response.parameters:
                state.parameters[param.name] = param.value

        return response
