from pydantic import BaseModel

from osa_tool.config.settings import ConfigManager
from osa_tool.core.git.git_agent import GitAgent
from osa_tool.scheduler.workflow_manager import WorkflowManager


class OSAConfig(BaseModel):
    """
    Global, read-only configuration.
    Initialized once per session.
    """

    config_manager: ConfigManager
    git_agent: GitAgent
    workflow_manager: WorkflowManager

    # For git_agent
    create_fork: bool = True
    create_pull_request: bool = True

    # Clean
    delete_dir: bool = False

    enable_replanning: bool = True
    enable_memory: bool = True
    dry_run: bool = False

    class Config:
        arbitrary_types_allowed = True
