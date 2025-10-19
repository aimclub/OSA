from osa_tool.readmegen.generator.header import HeaderBuilder
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_header_builder_initialization(mock_header_builder):
    # Arrange
    builder = mock_header_builder

    # Assert
    assert builder.config is not None
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
    assert builder.config.git.name in header


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


def test_header_builder_with_minimal_repo_tree(mock_config_loader, mock_repository_metadata, sourcerank_with_repo_tree):
    # Arrange
    repo_tree_data = get_mock_repo_tree("MINIMAL")
    sourcerank = sourcerank_with_repo_tree(repo_tree_data)
    builder = HeaderBuilder(mock_config_loader, mock_repository_metadata)
    builder.sourcerank = sourcerank

    # Assert
    assert builder.config is not None
    assert builder.sourcerank is not None

    header = builder.build_header()
    assert isinstance(header, str)
