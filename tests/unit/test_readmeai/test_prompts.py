from unittest.mock import patch

import logging
import pytest

from readmeai.config.settings import ConfigLoader, Settings
from readmeai.ingestion.models import RepositoryContext
from readmeai.models.prompts import (
    get_prompt_context,
    get_prompt_template,
    inject_prompt_context,
    set_additional_contexts,
)

logging.getLogger("readmeai.config.settings").setLevel(logging.CRITICAL)
logging.getLogger("readmeai.models.prompts").setLevel(logging.CRITICAL)


def test_get_prompt_context_found(config_loader_fixture: ConfigLoader):
    """Test the retrieval of a prompt context."""
    with (
        patch(
            "readmeai.models.prompts.get_prompt_template",
            return_value="Hello, {name}!",
        ),
        patch(
            "readmeai.models.prompts.inject_prompt_context",
            return_value="Hello, World!",
        ),
    ):
        result = get_prompt_context(
            config_loader_fixture.prompts,
            "greeting",
            {"name": "World"},
        )
        assert result == "Hello, World!"


def test_get_prompt_context_not_found(config_loader_fixture: ConfigLoader):
    """Test the retrieval of a prompt context."""
    with patch("readmeai.models.prompts.get_prompt_template", return_value=""):
        result = get_prompt_context(
            config_loader_fixture.prompts, "unknown", {}
        )
        assert result == ""


def test_get_prompt_template(config_loader_fixture: ConfigLoader):
    """Test the retrieval of a prompt template."""
    assert "Hello!" in get_prompt_template(
        config_loader_fixture.prompts, "core_features"
    )


def test_inject_prompt_context_success(
    config_fixture: Settings,
    config_loader_fixture: ConfigLoader,
    dependencies_fixture: list[str],
    repository_context_fixture: RepositoryContext,
    file_summaries_fixture: list[tuple[str, str]],
):
    """Test the injection of a prompt context."""
    context = get_prompt_context(
        config_loader_fixture.prompts,
        "core_features",
        {
            "name": config_fixture.git.name,
            "dependencies": dependencies_fixture,
            "quickstart": repository_context_fixture.quickstart,
            "file_summary": file_summaries_fixture,
        },
    )
    assert config_fixture.git.name in context


def test_inject_prompt_context_missing_key(
        caplog: pytest.LogCaptureFixture
):
    template = "This is {a} and {b}."
    context = {"a": "A"}
    assert inject_prompt_context(template, context) == ""


def test_set_additional_contexts(
    config_fixture: Settings,
    repository_context_fixture: RepositoryContext,
    file_summaries_fixture: list[tuple[str]],
):
    """Test the generation of additional prompts."""
    result = set_additional_contexts(
        config_fixture,
        repository_context_fixture,
        file_summaries_fixture
    )
    assert len(result) == 2
    assert result[0]["type"] == "core_features"
    assert result[1]["type"] == "overview"
    assert result[0]["context"]["file_summary"] == file_summaries_fixture
