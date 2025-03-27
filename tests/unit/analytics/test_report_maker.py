import os


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
