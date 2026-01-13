from pydantic import BaseModel

from osa_tool.config.settings import ConfigLoader
from osa_tool.git_agent.git_agent import GitAgent
from osa_tool.scheduler.workflow_manager import WorkflowManager


class OSAConfig(BaseModel):
    """
    Global, read-only configuration.
    Initialized once per session.
    """

    config_loader: ConfigLoader
    git_agent: GitAgent
    workflow_manager: WorkflowManager

    # For git_agent
    create_fork: bool = True
    create_pull_request: bool = True

    enable_replanning: bool = True
    enable_memory: bool = True
    dry_run: bool = False

    class Config:
        arbitrary_types_allowed = True
