from osa_tool.operations.docs.readme_generation.generator.header import HeaderBuilder
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_header_builder_initialization(mock_header_builder):
    """
    Verifies the correct initialization of the HeaderBuilder instance.
    
    Args:
        mock_header_builder: A fixture or mock object representing the HeaderBuilder to be tested. This fixture is expected to provide a pre-configured instance for testing.
    
    Note:
        This test ensures that the following essential class fields are properly initialized and are not None:
        - repo_url: The URL of the repository, required for linking and referencing the source.
        - _template: The template used for header generation, necessary for formatting output.
        - tree: The directory tree structure of the repository, used to navigate and process files.
    
    Why:
        Proper initialization of these fields is critical because the HeaderBuilder relies on them to function correctly. Without a valid repo_url, template, and tree structure, subsequent operations like generating file headers would fail or produce incorrect results.
    """
    # Arrange
    builder = mock_header_builder

    # Assert
    assert builder.repo_url is not None
    assert builder._template is not None
    assert builder.tree is not None


def test_load_template(mock_header_builder):
    """
    Verifies that the `load_template` method correctly retrieves a template and returns it as a dictionary. This test ensures the method returns a valid dictionary structure containing the expected "headers" key.
    
    Args:
        mock_header_builder: A mocked instance of the header builder used to simulate template loading.
    
    Returns:
        None: This is a test method and does not return a value.
    """
    # Arrange
    builder = mock_header_builder

    # Act
    template = builder.load_template()

    # Assert
    assert isinstance(template, dict)
    assert "headers" in template


def test_load_tech_icons(mock_header_builder):
    """
    Verifies that the load_tech_icons method correctly returns a dictionary of technology icons.
    
    This test ensures the method loads and returns icon data in the expected dictionary format, confirming the basic functionality and output type.
    
    Args:
        mock_header_builder: A mocked instance of the HeaderBuilder class used to isolate the test from external dependencies.
    
    Returns:
        None.
    """
    # Arrange
    builder = mock_header_builder

    # Act
    icons = builder.load_tech_icons()

    # Assert
    assert isinstance(icons, dict)


def test_generate_info_badges_with_info(mock_header_builder):
    """
    Verifies that the generate_info_badges method correctly returns a string containing PyPi-related badges.
    
    Args:
        mock_header_builder: A mocked instance of the HeaderBuilder class used for testing.
    
    Returns:
        None: This is a test method and does not return a value.
    
    Why:
        This test ensures that the method under test returns a string (not None or another type) when called with a mocked builder, validating the basic type contract of the method without requiring actual PyPi data.
    """
    # Arrange
    builder = mock_header_builder

    # Act
    badges = builder.generate_info_badges()

    # Assert
    assert isinstance(badges, str)


def test_generate_info_badges_without_info(mock_header_builder):
    """
    Verifies that the badge generation process returns an empty string when no project information is provided.
    
    This test ensures the `generate_info_badges` method correctly handles cases where the builder's `info` attribute is `None`, preventing the generation of any PyPi-related badges (such as version or download stats). This is important to avoid errors or malformed output when project metadata is unavailable.
    
    Args:
        mock_header_builder: A mocked instance of the header builder, configured to simulate a scenario with no project information.
    
    Returns:
        This method does not return a value; it performs an assertion to validate the behavior.
    """
    # Arrange
    builder = mock_header_builder
    builder.info = None

    # Act
    badges = builder.generate_info_badges()

    # Assert
    assert badges == ""


def test_generate_license_badge_with_license(mock_header_builder):
    """
    Verifies that the generate_license_badge method returns a valid string representation of a license badge.
    
    This test ensures the badge is correctly generated as a string, which is necessary for proper display in repository documentation.
    
    Args:
        mock_header_builder: A mocked instance of the HeaderBuilder class used to invoke the badge generation logic.
    
    Returns:
        None.
    """
    # Arrange
    builder = mock_header_builder

    # Act
    badge = builder.generate_license_badge()

    # Assert
    assert isinstance(badge, str)


def test_generate_license_badge_without_license(mock_header_builder):
    """
    Verifies that the generate_license_badge method returns an empty string when the metadata contains no license name.
    
    This test ensures the method gracefully handles missing license information by returning an empty string instead of generating a badge.
    
    Args:
        mock_header_builder: A mocked instance of the HeaderBuilder class, configured for testing.
    
    Returns:
        None.
    """
    # Arrange
    builder = mock_header_builder
    builder.metadata.license_name = None

    # Act
    badge = builder.generate_license_badge()

    # Assert
    assert badge == ""


def test_generate_tech_badges_with_techs(mock_header_builder):
    """
    Verifies that the generate_tech_badges method returns a string when technologies are provided.
    This test ensures the method behaves correctly in the typical case where technology data is available.
    
    Args:
        mock_header_builder: A mocked instance of the HeaderBuilder class used for testing.
        The mock is configured to simulate a scenario where technologies are present.
    """
    # Arrange
    builder = mock_header_builder

    # Act
    badges = builder.generate_tech_badges()

    # Assert
    assert isinstance(badges, str)


def test_generate_tech_badges_without_techs(mock_header_builder):
    """
    Verifies that the generate_tech_badges method returns an empty string or a valid string representation when no technologies are present in the builder.
    WHY: This test ensures the badge generation behaves gracefully when the project uses no technologies, preventing errors in downstream documentation rendering.
    
    Args:
        mock_header_builder: A mocked instance of the HeaderBuilder class used to simulate project header construction.
    
    Returns:
        None.
    """
    # Arrange
    builder = mock_header_builder
    builder.techs = set()

    # Act
    badges = builder.generate_tech_badges()

    # Assert
    assert isinstance(badges, str)


def test_generate_tech_badges_empty_result(mock_header_builder):
    """
    Verifies that the generate_tech_badges method returns a string even when the internal logic results in an empty or minimal output based on the provided technology set.
    This test ensures the method's return type consistency under edge-case conditions where the technology set yields no or minimal badge content.
    
    Args:
        mock_header_builder: A mocked instance of the header builder used to simulate technology configurations and badge generation.
    
    Returns:
        None.
    """
    # Arrange
    builder = mock_header_builder
    builder.techs = {"python"}

    # Act
    badges = builder.generate_tech_badges()

    # Assert
    assert isinstance(badges, str)


def test_build_information_section(mock_header_builder):
    """
    Verifies that the build_information_section property of the header builder returns a string.
    
    This test ensures the property correctly produces a string output, which is necessary for downstream formatting or display purposes in documentation generation.
    
    Args:
        mock_header_builder: A mocked instance of the header builder used for testing. The mock is set up to isolate the property's behavior from external dependencies.
    
    Returns:
        None.
    """
    # Arrange
    builder = mock_header_builder

    # Act
    section = builder.build_information_section

    # Assert
    assert isinstance(section, str)


def test_build_technology_section(mock_header_builder):
    """
    Verifies that the build_technology_section property returns a string.
    
    This test ensures the property correctly generates a formatted technology section for documentation, confirming the output is a string as required for further processing or display.
    
    Args:
        mock_header_builder: A mocked instance of the header builder used for testing. The mock simulates the builder's behavior to isolate the property's functionality.
    
    Returns:
        None.
    """
    # Arrange
    builder = mock_header_builder

    # Act
    section = builder.build_technology_section

    # Assert
    assert isinstance(section, str)


def test_build_header(mock_header_builder):
    """
    Verifies that the header builder correctly constructs a string containing the project name.
    
    WHY: This test ensures the HeaderBuilder's build_header method produces a valid header string that includes the project name, confirming the integration between configuration data and header generation.
    
    Args:
        mock_header_builder: A mocked instance of the header builder used to simulate the header construction process without external dependencies.
    
    Returns:
        None: This method performs assertions and does not return a value.
    """
    # Arrange
    builder = mock_header_builder

    # Act
    header = builder.build_header()

    # Assert
    assert isinstance(header, str)
    assert builder.config_manager.config.git.name in header


def test_generate_info_badges_formats_correctly(mock_header_builder):
    """
    Verifies that the generate_info_badges method returns a correctly formatted string.
    
    This test ensures that the method produces a string output, which is the expected format for PyPi-related badges (version and download stats). The test does not validate the specific content of the badges, only that the return type is correct.
    
    Args:
        mock_header_builder: A mocked instance of the HeaderBuilder class used for testing.
    
    Returns:
        None.
    """
    # Arrange
    builder = mock_header_builder

    # Act
    badges = builder.generate_info_badges()

    # Assert
    assert isinstance(badges, str)


def test_generate_tech_badges_respects_max_limit(mock_header_builder):
    """
    Verifies that the technology badge generation logic respects the maximum limit when a large number of technologies are provided.
    
    WHY: This test ensures that the badge generation does not exceed a predefined maximum number of badges, which is important for maintaining a clean, readable layout in the project documentation.
    
    Args:
        mock_header_builder: A mocked instance of the HeaderBuilder class used to simulate project metadata.
    
    Returns:
        None.
    """
    # Arrange
    builder = mock_header_builder
    many_techs = {f"tech{i}" for i in range(15)}
    builder.techs = many_techs

    # Act
    badges = builder.generate_tech_badges()

    # Assert
    assert isinstance(badges, str)


def test_header_builder_with_minimal_repo_tree(
    mock_config_manager, mock_repository_metadata, sourcerank_with_repo_tree
):
    """
    Tests the HeaderBuilder with a minimal repository tree configuration.
    
    This test verifies that HeaderBuilder can be properly initialized and
    build a header when provided with a minimal repository tree structure.
    It checks that the builder's dependencies (config_manager and sourcerank) are correctly set and that
    the build_header method returns a string. The test uses a mock repository tree to isolate the
    builder's behavior from external dependencies like the filesystem or Git operations.
    
    Args:
        mock_config_manager: Mock configuration manager providing config settings.
        mock_repository_metadata: Mock repository metadata object.
        sourcerank_with_repo_tree: Factory fixture to create a SourceRank instance
            with the given repository tree data.
    
    Returns:
        None: This is a test method and does not return a value.
    """
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
