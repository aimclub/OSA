from pathlib import Path

import pytest
from unittest.mock import patch

from osa_tool.readmeai.config.settings import ConfigLoader
from osa_tool.readmeai.generators.builder import MarkdownBuilder
from osa_tool.readmeai.ingestion.models import RepositoryContext


@pytest.fixture
def markdown_builder(
        config_loader_fixture: ConfigLoader,
        repository_context_fixture: RepositoryContext,
        tmp_path: Path,
):
    return MarkdownBuilder(
        config_loader=config_loader_fixture,
        repo_context=repository_context_fixture,
        temp_dir=str(tmp_path),
    )


def test_build(markdown_builder: MarkdownBuilder):
    with (
        patch.object(
            MarkdownBuilder,
            "header_and_badges",
            new="Header and Badges",
        ),
        patch.object(
            markdown_builder.config.md,
            "overview",
            new="Overview",
        ),
        patch.object(
            markdown_builder.config.md,
            "table_of_contents",
            new="Table of Contents"
        ),
        patch.object(
            markdown_builder.config.md,
            "core_features",
            new="Core Features"
        ),
        patch.object(
            MarkdownBuilder,
            "installation_guide",
            new="Installation guide"
        ),
        patch.object(
            MarkdownBuilder,
            "examples",
            new="Examples"
        ),
        patch.object(
            MarkdownBuilder,
            "documentation",
            new="Documentation"
        ),
        patch.object(
            MarkdownBuilder,
            "getting_started_guide",
            new="Getting Started guide"
        ),
        patch.object(
            MarkdownBuilder,
            "contributing",
            new="Contributing"
        ),
        patch.object(
            MarkdownBuilder,
            "license",
            new="License"
        ),
        patch.object(
            MarkdownBuilder,
            "acknowledgments",
            new="Acknowledgements"
        ),
        patch.object(
            MarkdownBuilder,
            "contacts",
            new="Contacts"
        ),
        patch.object(
            MarkdownBuilder,
            "citation",
            new="Citation"
        ),
    ):
        result = markdown_builder.build()
        expected_output = "\n".join(
            [
                "Header and Badges",
                "Overview",
                "",
                "## Table of contents",
                "",
                "- [Core features](#core-features)",
                "- [Installation](#installation)",
                "- [Examples](#examples)",
                "- [Documentation](#documentation)",
                "- [Getting started](#getting-started)",
                "- [Contributing](#contributing)",
                "- [License](#license)",
                "- [Acknowledgments](#acknowledgments)",
                "- [Contacts](#contacts)",
                "- [Citation](#citation)",
                "",
                "---",
                "",
                "Core Features",
                "Installation guide",
                "Examples",
                "Documentation",
                "Getting Started guide",
                "Contributing",
                "License",
                "Acknowledgements",
                "Contacts",
                "Citation"
            ]
        )
        assert result == expected_output
