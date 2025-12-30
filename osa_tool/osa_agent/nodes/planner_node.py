import json
from typing import Optional, List

from osa_tool.analytics.metadata import RepositoryMetadata
from osa_tool.models.models import ModelHandlerFactory
from osa_tool.osa_agent.config import OSAAgentConfig
from osa_tool.osa_agent.state import OSAAgentState, AgentStatus
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder


class OSAPlannerNode:
    """
    Node responsible for generating execution plans based on the user input
    and repository analysis. Creates a sequence of tasks for repository processing.
    """

    def __init__(self, osa_agent_config: OSAAgentConfig):
        self.osa_agent_config = osa_agent_config
        self.prompts = self.osa_agent_config.prompts
        self.llm = ModelHandlerFactory.build(self.osa_agent_config.config_loader.config)
        self.max_retries = self.osa_agent_config.config_loader.config.llm.max_retries
        self.tools = self.osa_agent_config.tools

    def __call__(self, state: OSAAgentState) -> OSAAgentState:
        """
        Generate a plan based on user request and repository.
        Updates state.tasks with the plan.
        """
        # Prepare planning context
        plan = self._create_plan(
            user_request=state.user_request,
            repo_url=state.repo_url,
            repo_metadata=state.repo_metadata,
            attachment=state.attachment,
        )

        # Update state with plan
        state.tasks = plan
        state.status = AgentStatus.ANALYZING

        return state

    def _create_plan(
        self,
        user_request: str,
        repo_url: str,
        repo_metadata: Optional[RepositoryMetadata],
        attachment: Optional[str],
    ) -> List[str]:
        """
        Create execution plan as a list of task descriptions.
        """
        # Format tools description
        tools_description = self._format_tools_description()

        # Build planning prompt using configured prompts
        prompt = PromptBuilder.render(
            self.prompts.get("osa_agent.planner"),
            user_request=user_request,
            repo_url=repo_url,
            attachment=attachment,
            repo_metadata=repo_metadata,
            tools_description=tools_description,
        )

        # Execute planning with retries
        for attempt in range(self.max_retries):
            try:
                response = self.llm.send_request(prompt)

                # Parse the plan from response
                plan = json.loads(response)
                if plan:
                    return plan

            except Exception as e:
                logger.error(f"Planning attempt {attempt + 1} failed: {e}")

        return []

    def _format_tools_description(self) -> str:
        """
        Format ToolSpec objects into a string description for the prompt.
        """
        tools_lines = []
        for tool in self.tools:
            tool_desc = f"- {tool.name}: {tool.description}"
            if tool.args_schema:
                properties = tool.args_schema.get("properties", {})
                if properties:
                    args_list = []
                    for param_name, param_info in properties.items():
                        param_desc = param_info.get("description", "")
                        args_list.append(f"{param_name}: {param_desc}")
                    if args_list:
                        tool_desc += f" (args: {', '.join(args_list)})"
            tools_lines.append(tool_desc)

        return "\n".join(tools_lines)
