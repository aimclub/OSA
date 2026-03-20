from typing import Optional

from pydantic import BaseModel, Field, ValidationError, TypeAdapter


class PromptConfig(BaseModel):
    """
    Model for validating the structure of prompts loaded from prompt_for_scheduler.toml.
    """


    report: bool = Field(
        False,
        description="Generate an additional report describing the analyzed repository for user reference. Does not affect the repository itself.",
    )
    translate_dirs: bool = Field(
        False, description="Translate directory and file names to English if they are not already in English."
    )
    docstring: bool = Field(False, description="Generate docstrings for functions and classes if .py files is present.")
    ensure_license: Optional[str] = Field(
        None,
        description="Generate a license file for the repository if missing. Set to 'bsd-3', 'mit', or 'ap2' to enable. If None, no license is added.",
    )
    community_docs: bool = Field(
        False,
        description="Generate community-related files such as CODE_OF_CONDUCT.md, PULL_REQUEST_TEMPLATE.md, and other supporting documentation.",
    )
    readme: bool = Field(
        False,
        description="Generate a README file for the repository if it is missing or of insufficient quality. If a clear and well-structured README is detected, this should be set to False.",
    )
    organize: bool = Field(
        False,
        description="Organize the repository by adding 'tests' and 'examples' directories if they do not already exist.",
    )
    about: bool = Field(False, description="Generate About section for the repository if it is missing.")

    model_config = {"extra": "ignore"}

    @classmethod
    def safe_validate(cls, data: dict) -> "PromptConfig":
        """
        Validate data with fallback to default values for invalid or missing fields.
        
        This class method ensures robust configuration creation by validating input data
        against the model's field definitions. If a field is missing, invalid, or fails
        validation, it gracefully falls back to the field's default value. This prevents
        configuration errors from crashing the system and guarantees a valid PromptConfig
        instance is always returned.
        
        Args:
            data: A dictionary containing configuration data to validate. Keys should
                  correspond to field names defined in the PromptConfig model.
        
        Returns:
            A PromptConfig instance populated with validated data, using defaults for
            any fields that were missing or invalid in the input.
        """
        validated_data = {}

        for field_name, field in cls.model_fields.items():
            value = data.get(field_name, field.default)
            adapter = TypeAdapter(field.annotation)
            try:
                validated_value = adapter.validate_python(value)
            except ValidationError:
                validated_value = field.default
            validated_data[field_name] = validated_value

        return cls(**validated_data)
