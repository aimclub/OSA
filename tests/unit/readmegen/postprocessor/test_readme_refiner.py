import json

import pytest

import osa_tool.readmegen.postprocessor.readme_refiner as refiner_module
from osa_tool.readmegen.postprocessor.readme_refiner import ReadmeRefiner
from tests.utils.fixtures.readmegen_readme_refiner_fixtures import DummyLLM


def test_parse_generated_readme_basic(mock_config_loader, load_metadata_prompts):
    # Arrange
    new_readme = """[![badge](url)]

## Introduction
This is the introduction.

## Usage
How to use."""
    rr = ReadmeRefiner(mock_config_loader, new_readme)

    # Act
    sections = rr.parse_generated_readme()

    # Assert
    assert "badges" in sections
    assert "Introduction" in sections
    assert "Usage" in sections
    assert sections["badges"].startswith("[![badge]")
    assert "introduction" in sections["Introduction"].lower()


def test_parse_generated_readme_handles_indented_headers(mock_config_loader, load_metadata_prompts):
    # Arrange
    new_readme = """   ## Features
Content here"""
    rr = ReadmeRefiner(mock_config_loader, new_readme)
    # Act
    sections = rr.parse_generated_readme()

    # Assert
    assert "Features" in sections
    assert "Content here" in sections["Features"]


def test_parse_generated_readme_empty_sections(mock_config_loader, load_metadata_prompts):
    # Arrange
    new_readme = """## EmptySection

## NonEmpty
Has content"""
    rr = ReadmeRefiner(mock_config_loader, new_readme)

    # Act
    sections = rr.parse_generated_readme()

    # Assert
    assert sections["EmptySection"] == ""
    assert "Has content" in sections["NonEmpty"]


def test_build_readme_from_sections_skips_empty():
    # Arrange
    sections = {"badges": "BADGE", "Intro": "   ", "Usage": "Use it"}

    # Act
    result = ReadmeRefiner.build_readme_from_sections(sections)

    # Assert
    assert "BADGE" in result
    assert "## Usage" in result
    assert "Intro" not in result


def test_build_readme_from_sections_order_preserved():
    # Arrange
    sections = {
        "badges": "BADGE",
        "A": "aaa",
        "B": "bbb",
    }

    # Act
    result = ReadmeRefiner.build_readme_from_sections(sections)

    # Assert
    assert result.startswith("BADGE")
    assert result.index("## A") < result.index("## B")


def test_refine_integration_with_mocked_llm(monkeypatch, mock_config_loader):
    # Arrange
    dummy_llm = DummyLLM()
    monkeypatch.setattr(refiner_module, "LLMClient", lambda cfg: dummy_llm)

    new_readme = """BADGES
## Introduction
Something
"""
    rr = ReadmeRefiner(mock_config_loader, new_readme)

    # Act
    result = rr.refine()

    # Assert
    assert "Introduction" in dummy_llm.called_with
    assert "badges" in dummy_llm.called_with
    assert "## Introduction" in result
    assert "Usage text" in result
    assert result.startswith("BADGES")


def test_refine_invalid_json(monkeypatch, mock_config_loader):
    # Arrange
    dummy_llm = DummyLLM(response="not-a-json")
    monkeypatch.setattr(refiner_module, "LLMClient", lambda cfg: dummy_llm)

    new_readme = """## Intro
Some text"""
    rr = ReadmeRefiner(mock_config_loader, new_readme)

    # Assert
    with pytest.raises(json.JSONDecodeError):
        rr.refine()
