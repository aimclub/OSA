from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from reportlab.platypus import Table, Paragraph, ListFlowable, Flowable

from osa_tool.operations.analysis.repository_report.report_maker import ReportGenerator


@pytest.fixture
def mock_git_agent(mock_repository_metadata):
    """
    Mock a GitAgent instance with specified repository metadata.
    
    This function creates a MagicMock object to simulate a GitAgent, primarily for testing purposes. It allows the injection of predefined repository metadata, enabling isolated unit tests that rely on GitAgent behavior without requiring actual repository access or complex setup.
    
    Args:
        mock_repository_metadata: The repository metadata to assign to the mocked GitAgent's metadata attribute.
    
    Returns:
        A MagicMock object configured as a GitAgent, with its metadata set to the provided mock_repository_metadata.
    """
    git_agent = MagicMock()
    git_agent.metadata = mock_repository_metadata
    return git_agent


def test_report_generator_init(mock_config_manager, mock_git_agent):
    """
    Tests the initialization of the ReportGenerator class to ensure all attributes are correctly assigned.
    
    Args:
        mock_config_manager: A mocked configuration manager providing repository settings.
        mock_git_agent: A mocked Git agent providing repository metadata.
    
    Attributes Initialized:
        text_generator: An instance of TextGenerator used for generating report content.
        repo_url: The URL of the repository being analyzed.
        osa_url: The hardcoded URL for the OSA project.
        metadata: Metadata information retrieved from the Git agent.
        filename: The generated name for the PDF report file.
        output_path: The absolute path where the report will be saved.
        logo_path: The path to the OSA logo image used in the report.
    
    Why:
        This test verifies that the ReportGenerator constructor properly sets up all necessary components
        for generating a repository report, using mocked dependencies to isolate the initialization logic.
        It ensures that paths are correctly resolved and that the TextGenerator is instantiated with the
        expected arguments.
    """
    # Arrange
    expected_metadata = mock_git_agent.metadata
    expected_repo_url = mock_config_manager.config.git.repository
    expected_filename = f"{expected_metadata.name}_report.pdf"
    expected_output_path = Path.cwd() / expected_filename
    expected_logo_path = Path(".") / "docs" / "images" / "osa_logo.PNG"

    with (
        patch("osa_tool.operations.analysis.repository_report.report_maker.osa_project_root", return_value="."),
        patch("osa_tool.operations.analysis.repository_report.report_maker.TextGenerator") as mock_text_generator,
    ):
        # Act
        report_generator = ReportGenerator(mock_config_manager, mock_git_agent, False)

        # Assert
        assert isinstance(report_generator.text_generator, MagicMock)
        assert report_generator.repo_url == expected_repo_url
        assert report_generator.osa_url == "https://github.com/aimclub/OSA"
        assert report_generator.metadata == expected_metadata
        assert report_generator.filename == expected_filename
        assert Path(report_generator.output_path) == expected_output_path
        assert Path(report_generator.logo_path) == expected_logo_path
        mock_text_generator.assert_called_once_with(mock_config_manager, mock_git_agent.metadata)


def test_table_builder_without_coloring():
    """
    Verifies that the table_builder method correctly creates a Table object when coloring is disabled.
    
    This test ensures that the generated Table instance contains the expected data and column widths, and that it is an instance of the correct class. The test is important because it validates that the table_builder method functions properly without color formatting, which is a common configuration for plain-text or non-interactive outputs.
    
    Args:
        data: A list of lists representing the table rows and columns.
        w_first_col: The width for the first column.
        w_second_col: The width for the second column.
    
    Returns:
        None
    """
    # Arrange
    data = [["Feature", "Status"], ["README", "✓"], ["License", "✗"]]
    w_first_col, w_second_col = 100, 200

    # Act
    table = ReportGenerator.table_builder(data, w_first_col, w_second_col, coloring=False)

    # Assert
    assert isinstance(table, Table)
    assert table._argW == [w_first_col, w_second_col]
    assert table._cellvalues == data


def test_table_builder_with_coloring():
    """
    Verifies that the table_builder method correctly creates a Table object with coloring enabled.
    
    This test case ensures that when the ReportGenerator's table builder is called with specific data, column widths, and the coloring flag set to True, it returns a Table instance with the expected internal cell values and column width configurations. The test validates that the coloring flag is properly passed through and that the Table's internal state matches the provided inputs.
    
    Args:
        None
    
    Returns:
        None
    """
    # Arrange
    data = [["Check", "Pass"], ["Test A", "✓"], ["Test B", "✗"]]
    w_first_col, w_second_col = 80, 180

    # Act
    table = ReportGenerator.table_builder(data, w_first_col, w_second_col, coloring=True)

    # Assert
    assert isinstance(table, Table)
    assert table._argW == [w_first_col, w_second_col]
    assert table._cellvalues == data


def test_generate_qr_code(tmp_path, mock_config_manager, monkeypatch, mock_git_agent):
    """
    Verifies that the QR code generation process correctly creates a file on the filesystem.
    
    WHY: This test ensures the ReportGenerator's QR code generation functionality works end-to-end by confirming the output file is physically created, validating the integration of QR code library calls and file system operations.
    
    Args:
        tmp_path: A pytest fixture providing a temporary directory unique to the test invocation.
        mock_config_manager: A mocked configuration manager used to initialize the ReportGenerator.
        monkeypatch: A pytest fixture used to safely patch attributes or environment variables.
        mock_git_agent: A mocked git agent used to initialize the ReportGenerator.
    
    Returns:
        None. This is a test method; assertions are used to verify behavior.
    """
    # Arrange
    monkeypatch.chdir(tmp_path)
    report_generator = ReportGenerator(mock_config_manager, mock_git_agent, False)

    # Act
    qr_path = report_generator.generate_qr_code()

    # Assert
    assert Path(qr_path).exists()

    # Cleanup
    Path(qr_path).unlink()


def test_header(mock_config_manager, mock_git_agent):
    """
    Verifies that the header method of the ReportGenerator class correctly produces the expected report header elements.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the ReportGenerator.
        mock_git_agent: A mocked git agent instance used to initialize the ReportGenerator.
    
    The test creates a ReportGenerator instance with the provided mocks and a False flag (likely indicating a non-dry run). It then calls the header method and asserts that the returned value is a list containing exactly two Paragraph objects. It further checks that the first paragraph includes the text "Repository Analysis Report" and the second paragraph includes the text "for". This ensures the header generates the correct structure and content for the report's introductory section.
    """
    # Arrange
    report_generator = ReportGenerator(mock_config_manager, mock_git_agent, False)

    # Act
    header_elements = report_generator.header()

    # Assert
    assert isinstance(header_elements, list)
    assert all(isinstance(el, Paragraph) for el in header_elements)
    assert len(header_elements) == 2
    assert "Repository Analysis Report" in header_elements[0].getPlainText()
    assert "for" in header_elements[1].getPlainText()


def test_draw_images_and_tables(tmp_path, mock_config_manager, monkeypatch, mock_git_agent):
    """
    Verifies that the draw_images_and_tables method correctly renders images, links, lines, and tables onto a report canvas.
    
    This test ensures the ReportGenerator's draw_images_and_tables method properly integrates visual and structural elements into the PDF canvas. It checks that the expected number of drawing operations are performed and that the table generator is invoked.
    
    Args:
        tmp_path: A temporary directory path provided by pytest for file system operations.
        mock_config_manager: A mocked configuration manager instance used to initialize the report generator.
        monkeypatch: A pytest fixture used to safely patch or modify objects, dictionaries, or os.environ.
        mock_git_agent: A mocked git agent instance used to handle repository operations.
    
    Returns:
        None.
    """
    # Arrange
    monkeypatch.chdir(tmp_path)
    report_generator = ReportGenerator(mock_config_manager, mock_git_agent, False)
    canvas_mock = MagicMock()
    doc_mock = MagicMock()
    report_generator.table_generator = MagicMock(return_value=(MagicMock(), MagicMock()))

    # Act
    report_generator.draw_images_and_tables(canvas_mock, doc_mock)

    # Assert
    assert canvas_mock.drawImage.call_count == 2
    assert canvas_mock.linkURL.call_count == 2
    assert canvas_mock.line.call_count == 2
    assert report_generator.table_generator.called


def test_table_generator_returns_two_tables(mock_config_manager, mock_git_agent):
    """
    Verifies that the table_generator method of the ReportGenerator class returns exactly two Table objects.
    
    This test ensures the method's output structure is correct, confirming that the generator produces the expected number of tables for reporting purposes.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used to initialize the generator.
        mock_git_agent: A mocked git agent instance used to initialize the generator.
    """
    # Arrange
    generator = ReportGenerator(mock_config_manager, mock_git_agent, False)

    # Act
    table1, table2 = generator.table_generator()

    # Assert
    assert isinstance(table1, Table)
    assert isinstance(table2, Table)


def test_body_first_part_returns_bullet_list(mock_config_manager, mock_git_agent):
    """
    Verifies that the body_first_part method returns a bulleted list containing the correct repository metadata.
    This test ensures the report generator correctly formats and includes essential repository details in the report body.
    
    Args:
        mock_config_manager: A mocked configuration manager instance used for report settings.
        mock_git_agent: A mocked git agent instance used to retrieve repository information.
    
    Asserts:
        - The returned object is an instance of ListFlowable.
        - The list contains exactly three items.
        - Each item in the list contains one of the expected metadata keys: "Repository Name", "Owner", or "Created at".
    """
    # Arrange
    generator = ReportGenerator(mock_config_manager, mock_git_agent, False)

    # Act
    bullet_list = generator.body_first_part()

    # Assert
    assert isinstance(bullet_list, ListFlowable)
    assert len(bullet_list._content) == 3
    assert all(
        any(key in item.text for key in ("Repository Name", "Owner", "Created at")) for item in bullet_list._content
    )


def test_body_second_part_returns_story_elements(
    mock_config_manager, text_generator_instance, monkeypatch, mock_git_agent
):
    """
    Verifies that the body_second_part method of ReportGenerator returns a list of story elements.
    This test ensures the generated documentation section contains the expected structural components, such as repository structure, README analysis, and recommendations, which are essential for comprehensive project documentation.
    
    Args:
        mock_config_manager: A mocked configuration manager instance to provide configuration without external dependencies.
        text_generator_instance: A tuple containing a text generator instance and its associated data, used to simulate text generation during the report creation.
        monkeypatch: The pytest monkeypatch fixture for modifying objects or environment variables during the test.
        mock_git_agent: A mocked git agent instance for simulating repository operations without actual Git interactions.
    
    Returns:
        This method does not return a value; it performs assertions to validate the output of body_second_part.
    """
    # Arrange
    report_generator = ReportGenerator(mock_config_manager, mock_git_agent, False)
    report_generator.text_generator, _ = text_generator_instance

    # Act
    story = report_generator.body_second_part()

    # Assert
    assert isinstance(story, list)
    assert all(isinstance(item, Flowable) for item in story)
    assert any("Repository Structure" in para.getPlainText() for para in story if isinstance(para, Paragraph))
    assert any("README Analysis" in para.getPlainText() for para in story if isinstance(para, Paragraph))
    assert any("Recommendations" in para.getPlainText() for para in story if isinstance(para, Paragraph))


def test_build_pdf_creates_output_file(
    tmp_path, mock_config_manager, text_generator_instance, monkeypatch, mock_git_agent
):
    """
    Verifies that the build_pdf method successfully creates a non-empty PDF file at the expected location.
    
    This test ensures the PDF generation process completes without errors and produces a valid output file with the correct naming convention and non-zero size.
    
    Args:
        tmp_path: A pytest fixture providing a temporary directory path for the test execution. The test changes the working directory to this path to isolate file output.
        mock_config_manager: A mocked configuration manager used to initialize the ReportGenerator, providing controlled configuration without external dependencies.
        text_generator_instance: A tuple containing a text generator instance and its associated data. The instance is assigned to the ReportGenerator to supply the content for the PDF.
        monkeypatch: A pytest fixture used to safely patch attributes and environment variables. Here, it is used to change the current working directory to the temporary path.
        mock_git_agent: A mocked git agent used to initialize the ReportGenerator, simulating Git operations without requiring a real repository.
    
    Returns:
        None.
    """
    # Arrange
    monkeypatch.chdir(tmp_path)
    report_generator = ReportGenerator(mock_config_manager, mock_git_agent, False)
    report_generator.text_generator, _ = text_generator_instance

    # Act
    report_generator.build_pdf()

    # Assert
    output_path = Path(report_generator.output_path)
    assert output_path.exists()
    assert output_path.name == f"{report_generator.metadata.name}_report.pdf"
    assert output_path.stat().st_size > 0
