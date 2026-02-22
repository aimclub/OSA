from typing import Optional, List, Dict, Any, Literal

from pydantic import BaseModel, Field, ConfigDict

from osa_tool.core.git.metadata import RepositoryMetadata
from osa_tool.core.models.agent_status import AgentStatus
from osa_tool.core.models.task import Task
from osa_tool.tools.repository_analysis.models import RepositoryData


class OSAState(BaseModel):
    # User input
    repo_url: Optional[str] = None
    attachment: Optional[str] = None

    # Unified request flow
    active_request: Optional[str] = None
    active_request_source: Optional[Literal["user", "reviewer"]] = None

    # Unified clarification mechanism
    clarification_attempts: int = 3
    clarification_required: bool = False
    clarification_agent: Optional[str] = None
    clarification_type: Literal["single_question", "user_request", "review", "multi_question"] = "single_question"
    clarification_payload: Optional[dict] = None
    clarification_answer: Optional[Any] = None

    # Intent
    intent: Optional[str] = None
    task_scope: Optional[str] = None
    intent_confidence: Optional[float] = None

    # Execution metadata
    session_id: str
    status: AgentStatus = AgentStatus.INIT
    active_agent: Optional[str] = None

    # Repository
    repo_path: Optional[str] = None
    repo_prepared: bool = False
    repo_data: Optional[RepositoryData] = None
    repo_metadata: Optional[RepositoryMetadata] = None

    # Planning
    plan: List[Task] = Field(default_factory=list)
    plan_reasoning: Optional[str] = None
    missing_arguments: list = Field(default_factory=list)
    current_step_index: Optional[int] = None

    # Artifacts & memory
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    session_memory: List[Dict[str, Any]] = Field(default_factory=list)
    plan_history: List[List[Dict[str, Any]]] = Field(default_factory=list)

    # Reviewer feedback
    review_feedback: Optional[str] = None
    review_requires_new_intent: bool = False
    review_requires_new_task_scope: bool = False
    reviewer_summary: Optional[str] = None
    previous_plan_status: Optional[List[Task]] = None
    approval: bool = False
    # Limit Planner -> Executor -> Reviewer loop
    max_review_cycles: int = 3
    review_cycle_count: int = 0
    review_cycles_exhausted: bool = False

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def get_task(self, task_id: str) -> Optional[Task]:
        """Returns a Task by its id or None if not found"""
        for task in self.plan:
            if task.id == task_id:
                return task
        return None

    def __str__(self):
        plan_summary = [f"{t.id}: args={t.args}" for t in getattr(self, "plan", [])]
        missing_args_summary = [
            f"{item['task_id']}::{item['field']}" for item in getattr(self, "missing_arguments", [])
        ]

        return (
            f"OSAState(\n"
            f"  session_id={self.session_id},\n"
            f"  repo_url={self.repo_url},\n"
            f"  attachment={self.attachment},\n"
            f"  active_request={self.active_request},\n"
            f"  active_request_source={self.active_request_source},\n"
            f"  intent={self.intent}, intent_confidence={self.intent_confidence},\n"
            f"  task_scope={self.task_scope},\n"
            f"  repo_prepared={self.repo_prepared},\n"
            f"  active_agent={self.active_agent},\n"
            f"  current_step_index={self.current_step_index},\n"
            f"  status={self.status},\n"
            f"  plan_tasks=[{', '.join(plan_summary)}],\n"
            f"  missing_arguments=[{', '.join(missing_args_summary)}],\n"
            f"  review_feedback={self.review_feedback},\n"
            f"  review_requires_new_intent={self.review_requires_new_intent},\n"
            f"  approval={self.approval},\n"
            f"  review_cycle_count={self.review_cycle_count},\n"
            f"  max_review_cycles={self.max_review_cycles}\n"
            f")"
        )
