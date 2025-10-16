from pathlib import Path
from unittest.mock import patch, MagicMock

from reportlab.platypus import Table, Paragraph, ListFlowable, Flowable

from osa_tool.analytics.report_maker import ReportGenerator


def test_report_generator_init(mock_config_loader, mock_sourcerank, mock_repository_metadata):
    # Arrange
    expected_metadata = mock_repository_metadata
    expected_repo_url = mock_config_loader.config.git.repository
    expected_filename = f"{expected_metadata.name}_report.pdf"
    expected_output_path = Path.cwd() / expected_filename
    expected_logo_path = Path(".") / "docs" / "images" / "osa_logo.PNG"
    sourcerank_instance = mock_sourcerank()

    with (
        patch("osa_tool.analytics.report_maker.osa_project_root", return_value="."),
        patch("osa_tool.analytics.report_maker.TextGenerator") as mock_text_generator,
    ):
        # Act
        report_generator = ReportGenerator(mock_config_loader, sourcerank_instance, mock_repository_metadata)

        # Assert
        assert report_generator.config == mock_config_loader.config
        assert report_generator.sourcerank is sourcerank_instance
        assert isinstance(report_generator.text_generator, MagicMock)
        assert report_generator.repo_url == expected_repo_url
        assert report_generator.osa_url == "https://github.com/aimclub/OSA"
        assert report_generator.metadata == expected_metadata
        assert report_generator.filename == expected_filename
        assert Path(report_generator.output_path) == expected_output_path
        assert Path(report_generator.logo_path) == expected_logo_path
        mock_text_generator.assert_called_once_with(mock_config_loader, sourcerank_instance, mock_repository_metadata)


def test_table_builder_without_coloring():
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
    # Arrange
    data = [["Check", "Pass"], ["Test A", "✓"], ["Test B", "✗"]]
    w_first_col, w_second_col = 80, 180

    # Act
    table = ReportGenerator.table_builder(data, w_first_col, w_second_col, coloring=True)

    # Assert
    assert isinstance(table, Table)
    assert table._argW == [w_first_col, w_second_col]
    assert table._cellvalues == data


def test_generate_qr_code(tmp_path, mock_config_loader, mock_sourcerank, monkeypatch, mock_repository_metadata):
    # Arrange
    monkeypatch.chdir(tmp_path)
    report_generator = ReportGenerator(mock_config_loader, mock_sourcerank(), mock_repository_metadata)

    # Act
    qr_path = report_generator.generate_qr_code()

    # Assert
    assert Path(qr_path).exists()

    # Cleanup
    Path(qr_path).unlink()


def test_header(mock_config_loader, mock_sourcerank, mock_repository_metadata):
    # Arrange
    report_generator = ReportGenerator(mock_config_loader, mock_sourcerank(), mock_repository_metadata)

    # Act
    header_elements = report_generator.header()

    # Assert
    assert isinstance(header_elements, list)
    assert all(isinstance(el, Paragraph) for el in header_elements)
    assert len(header_elements) == 2
    assert "Repository Analysis Report" in header_elements[0].getPlainText()
    assert "for" in header_elements[1].getPlainText()


def test_draw_images_and_tables(tmp_path, mock_config_loader, mock_sourcerank, monkeypatch, mock_repository_metadata):
    # Arrange
    monkeypatch.chdir(tmp_path)
    report_generator = ReportGenerator(mock_config_loader, mock_sourcerank(), mock_repository_metadata)
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


def test_table_generator_returns_two_tables(mock_config_loader, mock_sourcerank, mock_repository_metadata):
    # Arrange
    generator = ReportGenerator(mock_config_loader, mock_sourcerank(), mock_repository_metadata)

    # Act
    table1, table2 = generator.table_generator()

    # Assert
    assert isinstance(table1, Table)
    assert isinstance(table2, Table)


def test_body_first_part_returns_bullet_list(mock_config_loader, mock_sourcerank, mock_repository_metadata):
    # Arrange
    generator = ReportGenerator(mock_config_loader, mock_sourcerank(), mock_repository_metadata)

    # Act
    bullet_list = generator.body_first_part()

    # Assert
    assert isinstance(bullet_list, ListFlowable)
    assert len(bullet_list._content) == 3
    assert all(
        any(key in item.text for key in ("Repository Name", "Owner", "Created at")) for item in bullet_list._content
    )


def test_body_second_part_returns_story_elements(
    mock_config_loader, mock_sourcerank, text_generator_instance, monkeypatch, mock_repository_metadata
):
    # Arrange
    report_generator = ReportGenerator(mock_config_loader, mock_sourcerank(), mock_repository_metadata)
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
    tmp_path, mock_config_loader, mock_sourcerank, text_generator_instance, monkeypatch, mock_repository_metadata
):
    # Arrange
    monkeypatch.chdir(tmp_path)
    report_generator = ReportGenerator(mock_config_loader, mock_sourcerank(), mock_repository_metadata)
    report_generator.text_generator, _ = text_generator_instance

    # Act
    report_generator.build_pdf()

    # Assert
    output_path = Path(report_generator.output_path)
    assert output_path.exists()
    assert output_path.name == f"{report_generator.metadata.name}_report.pdf"
    assert output_path.stat().st_size > 0
