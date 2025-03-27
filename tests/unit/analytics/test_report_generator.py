import pytest
import json

from unittest.mock import MagicMock, patch
from osa_tool.analytics.prompt_builder import RepositoryReport


# def test_make_request(text_generator):
#     # Arrange
#     mock_response = {
#         "compliance": "Compliant",
#         "missing_files": [],
#         "organization": "Well organized"
#     }
#     text_generator.model_handler.send_request.return_value = json.dumps(mock_response)
#     # Act
#     result = text_generator.make_request()
#     # Assert
#     assert isinstance(result, RepositoryReport)
#     # assert result.structure.compliance == "Compliant"
#     # assert result.structure.missing_files == []
#     # assert result.structure.organization == "Well organized"
#
#     # text_generator.model_handler.send_request.return_value = "invalid json"
#     # with pytest.raises(ValueError, match="JSON parsing error"):
#     #     text_generator.make_request()
#
#
# def test_build_prompt(text_generator):
#     with patch("builtins.open", new_callable=MagicMock) as mock_open:
#         mock_open.return_value.__enter__.return_value.read.return_value = "[prompt]\nmain_prompt='Project: {project_name}'"
#
#         with patch("tomllib.load", return_value={
#             "prompt": {"main_prompt": "Project: {project_name}"}}):
#             prompt = text_generator._build_prompt()
#             assert "Project: Mock Project" in prompt
#
#
# def test_extract_readme_content(text_generator):
#     with patch("os.path.exists", return_value=True), patch("builtins.open",
#                                                            new_callable=MagicMock) as mock_open:
#         mock_open.return_value.__enter__.return_value.read.return_value = "# Mock README"
#
#         content = text_generator._extract_readme_content()
#         assert content == "# Mock README"
#
#     with patch("os.path.exists", return_value=False):
#         content = text_generator._extract_readme_content()
#         assert content == "No README.md file"
#
#
# def test_extract_presence_files(text_generator):
#     files_presence = text_generator._extract_presence_files()
#     assert "README presence is True" in files_presence
#     assert "LICENSE presence is True" in files_presence
#     assert "Examples presence is False" in files_presence
#     assert "Documentation presence is True" in files_presence
