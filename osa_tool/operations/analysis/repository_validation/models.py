from pydantic import BaseModel, ConfigDict, Field


class ExtractedExperimentsResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    experiment_list: list[str] = Field(default_factory=list)


class Experiment(BaseModel):
    model_config = ConfigDict(validate_assignment=True)

    description_from_paper: str = ""
    # Implementation locations in the provided repository.
    impl_src_path: list[str] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)
    correspondence_percent: float | None = None


class ExperimentValidationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    implemented_in: list[str] = Field(default_factory=list)
    missing_critical_components: list[str] = Field(default_factory=list)
    correlation_percent: float = 0.0
