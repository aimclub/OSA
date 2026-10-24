import json
import os
import re

from osa_tool.operations.docs.readme_generation.sections.header import BADGE_STYLE, HeaderBuilder
from osa_tool.utils.utils import osa_project_root
from tests.utils.mocks.repo_trees import get_mock_repo_tree

ICONS_PATH = os.path.join(
    osa_project_root(),
    "operations",
    "docs",
    "readme_generation",
    "sections",
    "icons",
    "shieldsio_icons.json",
)


def test_header_builder_initialization(mock_header_builder):
    # Arrange
    builder = mock_header_builder

    # Assert
    assert builder.repo_url is not None
    assert builder._template is not None
    assert builder.tree is not None


def test_load_template(mock_header_builder):
    # Arrange
    builder = mock_header_builder

    # Act
    template = builder.load_template()

    # Assert
    assert isinstance(template, dict)
    assert "headers" in template


def test_load_tech_icons(mock_header_builder):
    # Arrange
    builder = mock_header_builder

    # Act
    icons = builder.load_tech_icons()

    # Assert
    assert isinstance(icons, dict)


def test_generate_info_badges_with_info(mock_header_builder):
    # Arrange
    builder = mock_header_builder

    # Act
    badges = builder.generate_info_badges()

    # Assert
    assert isinstance(badges, str)


def test_generate_info_badges_without_info(mock_header_builder):
    # Arrange
    builder = mock_header_builder
    builder.info = None

    # Act
    badges = builder.generate_info_badges()

    # Assert
    assert badges == ""


def test_generate_license_badge_with_license(mock_header_builder):
    # Arrange
    builder = mock_header_builder

    # Act
    badge = builder.generate_license_badge()

    # Assert
    assert isinstance(badge, str)


def test_generate_license_badge_without_license(mock_header_builder):
    # Arrange
    builder = mock_header_builder
    builder.metadata.license_name = None

    # Act
    badge = builder.generate_license_badge()

    # Assert
    assert badge == ""


def test_generate_tech_badges_with_techs(mock_header_builder):
    # Arrange
    builder = mock_header_builder

    # Act
    badges = builder.generate_tech_badges()

    # Assert
    assert isinstance(badges, str)


def test_generate_tech_badges_without_techs(mock_header_builder):
    # Arrange
    builder = mock_header_builder
    builder.techs = set()

    # Act
    badges = builder.generate_tech_badges()

    # Assert
    assert isinstance(badges, str)


def test_generate_tech_badges_empty_result(mock_header_builder):
    # Arrange
    builder = mock_header_builder
    builder.techs = {"python"}

    # Act
    badges = builder.generate_tech_badges()

    # Assert
    assert isinstance(badges, str)


def test_build_information_section(mock_header_builder):
    # Arrange
    builder = mock_header_builder

    # Act
    section = builder.build_information_section

    # Assert
    assert isinstance(section, str)


def test_build_technology_section(mock_header_builder):
    # Arrange
    builder = mock_header_builder

    # Act
    section = builder.build_technology_section

    # Assert
    assert isinstance(section, str)


def test_build_header(mock_header_builder):
    # Arrange
    builder = mock_header_builder

    # Act
    header = builder.build_header()

    # Assert
    assert isinstance(header, str)
    assert builder.config_manager.config.git.name in header


def test_generate_info_badges_formats_correctly(mock_header_builder):
    # Arrange
    builder = mock_header_builder

    # Act
    badges = builder.generate_info_badges()

    # Assert
    assert isinstance(badges, str)


def test_generate_tech_badges_respects_max_limit(mock_header_builder):
    # Arrange
    builder = mock_header_builder
    many_techs = {f"tech{i}" for i in range(15)}
    builder.techs = many_techs

    # Act
    badges = builder.generate_tech_badges()

    # Assert
    assert isinstance(badges, str)


def test_generate_tech_badges_substitutes_style_placeholder(mock_header_builder):
    # Arrange
    builder = mock_header_builder
    builder.techs = {"numpy", "scipy", "pytest"}

    # Act
    badges = builder.generate_tech_badges()

    # Assert
    # every shields.io URL ships a "{0}" placeholder; leaving it unsubstituted
    # put a literal "style={0}" into generated READMEs
    assert "{0}" not in badges
    assert badges.count(f"style={BADGE_STYLE}") == 3


def test_shipped_icon_urls_are_format_safe():
    # Arrange
    with open(ICONS_PATH, "r", encoding="utf-8") as f:
        icons = json.load(f)

    # Assert
    # a stray brace would make str.format raise during README generation
    assert icons
    for tech, entry in icons.items():
        url = entry[0]
        assert url.count("{0}") == 1, f"{tech}: expected exactly one style placeholder"
        assert not re.search(r"\{(?!0\})", url), f"{tech}: unexpected brace in {url}"
        assert "{0}" not in url.format(BADGE_STYLE)


def test_header_builder_with_minimal_repo_tree(
    mock_config_manager, mock_repository_metadata, sourcerank_with_repo_tree
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder = HeaderBuilder(mock_config_manager, mock_repository_metadata)
    builder.sourcerank = sourcerank

    # Assert
    assert builder.config_manager.config is not None
    assert builder.sourcerank is not None

    header = builder.build_header()
    assert isinstance(header, str)
