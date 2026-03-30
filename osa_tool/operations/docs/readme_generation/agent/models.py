"""Domain models for the README generation agent pipeline."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RepositoryContext(BaseModel):
    """Aggregated repository context collected during the first pipeline stage."""

    model_config = ConfigDict(extra="ignore")

    repo_tree: str = ""
    existing_readme: str = ""
    key_files: list[str] = Field(default_factory=list)
    key_files_content: str = ""
    examples_content: str = ""
    pdf_content: str | None = None
    repo_analysis: str | None = None
    readme_analysis: str | None = None
    article_analysis: str | None = None


class TaskIntent(BaseModel):
    """Result of intent analysis — what the user wants done and at what scope."""

    model_config = ConfigDict(extra="ignore")

    task_type: Literal["generate", "improve", "update"] = "generate"
    scope: Literal["full", "partial"] = "full"
    affected_sections: list[str] = Field(default_factory=list)
    incorporate_paper: bool = False
    reasoning: str = ""


class SectionSpec(BaseModel):
    """Plan entry describing one README section to produce."""

    model_config = ConfigDict(extra="ignore")

    name: str
    title: str
    description: str = ""
    strategy: Literal["llm", "deterministic", "keep_existing"] = "llm"
    priority: int = 0
    depends_on: list[str] = Field(default_factory=list)
    prompt_context_keys: list[str] = Field(default_factory=list)


class SectionResult(BaseModel):
    """Generated content for a single README section."""

    model_config = ConfigDict(extra="ignore")

    name: str
    title: str
    content: str = ""
    source: Literal["llm", "deterministic", "existing"] = "llm"
