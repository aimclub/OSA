import os
from unittest.mock import MagicMock, patch

from reportlab.platypus import ListFlowable, Table

from osa_tool.analytics.prompt_builder import (
    CodeDocumentation,
    OverallAssessment,
    ReadmeEvaluation,
    RepositoryReport,
    RepositoryStructure,
    YesNoPartial
)
from osa_tool.analytics.report_maker import ReportGenerator


def test_report_generator_initialization(report_generator):
    # Assert
    assert report_generator.repo_url == "https://github.com/testuser/testrepo.git"
    assert report_generator.metadata is not None
    assert report_generator.output_path.endswith("_report.pdf")


def test_generate_qr_code(report_generator):
    # Act
    qr_path = report_generator.generate_qr_code()
    # Assert
    assert qr_path.endswith("temp_qr.png")
    assert os.path.exists(qr_path)
    # TearDown
    os.remove(qr_path)


def test_table_builder(report_generator):
    # Arrange
    data = [["Header 1", "Header 2"], ["Row 1", "✓"], ["Row 2", "✗"]]
    # Act
    table = report_generator.table_builder(data, 100, 100, coloring=True)
    # Assert
    assert isinstance(table, Table)


@patch.object(ReportGenerator, 'generate_qr_code', return_value="temp_qr.png")
@patch("os.remove")
def test_draw_images_and_tables(mock_remove, mock_generate_qr_code, report_generator):
    # Arrange
    mock_canvas = MagicMock()
    mock_doc = MagicMock()
    # Act
    report_generator.draw_images_and_tables(mock_canvas, mock_doc)
    # Assert
    mock_canvas.drawImage.assert_called()
    mock_canvas.line.assert_called()
    mock_remove.assert_called_once_with("temp_qr.png")


def test_header(report_generator):
    # Act
    header_elements = report_generator.header()
    # Assert
    assert len(header_elements) == 2


def test_table_generator(report_generator):
    # Act
    table1, table2 = report_generator.table_generator()
    # Assert
    assert isinstance(table1, Table)
    assert isinstance(table2, Table)


def test_body_first_part(report_generator):
    # Arrange
    report_generator.metadata = MagicMock()
    report_generator.metadata.created_at = '2025-03-28T14:30:00Z'
    report_generator.metadata.owner = "testuser"
    report_generator.metadata.owner_url = "https://github.com/testuser"
    report_generator.metadata.name = "testrepo"
    report_generator.metadata.repo_url = "https://github.com/testuser/testrepo"
    # Act
    body_part = report_generator.body_first_part()
    # Assert
    assert isinstance(body_part, ListFlowable)


def test_body_second_part(report_generator):
    # Arrange
    report_generator.text_generator = MagicMock()
    report_generator.text_generator.make_request.return_value = RepositoryReport(
        structure=RepositoryStructure(
            compliance="Yes",
            missing_files=["file1.py", "file2.py"],
            organization="Well structured"
        ),
        readme=ReadmeEvaluation(
            readme_quality="High",
            project_description=YesNoPartial.YES,
            installation=YesNoPartial.PARTIAL,
            usage_examples=YesNoPartial.NO,
            contribution_guidelines=YesNoPartial.YES,
            license_specified=YesNoPartial.NO,
            badges_present=YesNoPartial.PARTIAL
        ),
        documentation=CodeDocumentation(
            tests_present=YesNoPartial.YES,
            docs_quality="Good",
            outdated_content=False
        ),
        assessment=OverallAssessment(
            key_shortcomings=["Missing tests", "No documentation"],
            recommendations=["Improve tests", "Update docs"]
        )
    )

    # Act
    story = report_generator.body_second_part()

    # Assert
    assert len(story) > 0

    # Repository Structure
    assert "Repository Structure" in story[0].getPlainText()
    assert "Compliance: Yes" in story[1].getPlainText()
    assert "Missing files: file1.py, file2.py" in story[2].getPlainText()
    assert "Organization: Well structured" in story[3].getPlainText()

    # README Analysis
    assert "README Analysis" in story[4].getPlainText()
    assert "Quality: High" in story[5].getPlainText()
    assert "Project description: Yes" in story[6].getPlainText()
    assert "Installation: Partial" in story[7].getPlainText()
    assert "Usage examples: No" in story[8].getPlainText()
    assert "Contribution guidelines: Yes" in story[9].getPlainText()
    assert "License specified: No" in story[10].getPlainText()
    assert "Badges present: Partial" in story[11].getPlainText()

    # Documentation
    assert "Documentation:" in story[12].getPlainText()
    assert "Tests present: Yes" in story[13].getPlainText()
    assert "Documentation quality: Good" in story[14].getPlainText()
    assert "Outdated content: No" in story[15].getPlainText()

    # Key Shortcomings
    assert "Key Shortcomings" in story[16].getPlainText()
    assert "- Missing tests" in story[17].getPlainText()
    assert "- No documentation" in story[18].getPlainText()

    # Recommendations
    assert "Recommendations" in story[19].getPlainText()
    assert "- Improve tests" in story[20].getPlainText()
    assert "- Update docs" in story[21].getPlainText()