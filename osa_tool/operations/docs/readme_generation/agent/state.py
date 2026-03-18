from typing import Any, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

from osa_tool.core.models.event import OperationEvent


class ReadmeState(BaseModel):
    """Mutable workflow state for the README generation sub-graph."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    # Inputs
    repo_url: str
    attachment: Optional[str] = None
    user_request: Optional[str] = None

    # Raw context (ContextCollectorNode)
    key_files: List[str] = Field(default_factory=list)
    key_files_content: str = ""
    existing_readme: str = ""
    repo_tree: str = ""
    examples_content: str = ""
    pdf_content: Optional[str] = None

    # Structured analysis (ContextCollectorNode)
    repo_analysis: Optional[str] = None
    readme_analysis: Optional[str] = None
    article_analysis: Optional[str] = None

    # Diagnosis (DiagnosisNode)
    generation_mode: Literal["full_regen", "targeted"] = "full_regen"
    readme_mode: Literal["standard", "article"] = "standard"
    target_sections: List[str] = Field(default_factory=list)
    generation_plan: Optional[str] = None

    # Generated content — standard mode
    core_features: Optional[Any] = None
    overview: Optional[str] = None
    getting_started: Optional[str] = None

    # Generated content — article mode
    file_summary: Optional[str] = None
    pdf_summary: Optional[str] = None
    content: Optional[str] = None
    algorithms: Optional[str] = None

    # Assembly & refinement
    readme_draft: Optional[str] = None
    readme_final: Optional[str] = None
    refinement_score: Optional[float] = None
    refinement_issues: List[str] = Field(default_factory=list)
    refinement_cycles: int = 0
    max_refinement_cycles: int = 3

    # Output
    events: List[OperationEvent] = Field(default_factory=list)
    error: Optional[str] = None
