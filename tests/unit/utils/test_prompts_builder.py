import pytest

from osa_tool.utils.prompts_builder import PromptBuilder, PromptLoader, PromptLoadError


def test_prompt_builder_success():
    # Arrange
    template = "Hello {name}"

    # Act
    result = PromptBuilder.render(template, name="Alice")

    # Assert
    assert result == "Hello Alice"


def test_prompt_builder_missing_argument():
    # Arrange
    template = "Hello {name}"

    # Assert
    with pytest.raises(Exception):
        PromptBuilder.render(template)


def test_prompt_builder_invalid_format():
    # Arrange
    template = "Hello {name"

    # Assert
    with pytest.raises(Exception):
        PromptBuilder.render(template, name="Bob")


def test_prompt_loader_load_files():
    # Arrange
    loader = PromptLoader()

    # Assert
    assert len(loader.cache) > 0
    for section, prompts in loader.cache.items():
        assert isinstance(prompts, dict)
        assert len(prompts) > 0


def test_prompt_loader_missing_prompt():
    # Arrange
    loader = PromptLoader()

    # Assert
    with pytest.raises(PromptLoadError):
        loader.get("no_such_prompt.preanalysis")


def test_prompt_loader_missing_section():
    # Arrange
    loader = PromptLoader()

    # Assert
    with pytest.raises(PromptLoadError):
        loader.get("readme.prompts.no_such_section")


def test_prompt_builder_format_real_template():
    # Arrange
    loader = PromptLoader()
    template = loader.get("readme.prompts.preanalysis")

    # Act
    rendered = PromptBuilder.render(template, repository_tree="test_tree", readme_content="test_readme")

    # Assert
    assert isinstance(rendered, str)
    assert len(rendered) > 0
    assert "Based on the repository file tree and README" in rendered


def test_prompt_loader_overrides_only_provided_prompt_keys(tmp_path):
    override_dir = tmp_path / "prompts"
    override_dir.mkdir()
    (override_dir / "paper_claims.toml").write_text(
        '[prompts]\nsection_filter_system = "custom section filter"\n',
        encoding="utf-8",
    )

    default_loader = PromptLoader()
    loader = PromptLoader(override_dirs=[override_dir])

    assert loader.get("paper_claims.section_filter_system") == "custom section filter"
    assert loader.get("paper_claims.claim_extraction_system") == default_loader.get(
        "paper_claims.claim_extraction_system"
    )
