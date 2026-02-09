from pydantic import BaseModel


class FinalizerPullRequestSummary(BaseModel):
    """Output of Finalizer agent."""

    summary: str
