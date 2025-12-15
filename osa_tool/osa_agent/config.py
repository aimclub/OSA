from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.git_agent.git_agent import GitAgent
from osa_tool.utils.prompts_builder import PromptLoader


class ToolSpec(BaseModel):
    """Declarative tool representation."""

    name: str
    description: str
    args_schema: Optional[dict] = None
    return_schema: Optional[dict] = None


class OSAAgentConfig(BaseModel):
    """
    High-level agent config.
    Can be constructed from CLI + config file + internal defaults.
    """

    config_loader: ConfigLoader
    git_agent: GitAgent
    sourcerank: SourceRank

    # Planner behavior
    enable_replanning: bool = True
    enable_memory: bool = True

    # Prompts
    prompts: PromptLoader

    # List of scenario agents
    scenario_agents: List[str]
    # Nodes for scenario agents
    scenario_agents_funcs: Dict[str, Any]

    # Tools
    tools: List[ToolSpec] = Field(default_factory=list)

    # Tasks
    tasks: List[str] = Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True
