import os
import pytest
from unittest.mock import MagicMock, mock_open, patch
from osa_tool.readmeai.config.settings import ConfigLoader
from osa_tool.osatreesitter.models import ModelHandlerFactory
from osa_tool.translation.dir_translator import DirectoryTranslator


class TestDirectoryTranslator:
    @pytest.fixture
    def mock_walk_data(self):
        return [
            (os.path.normpath("/repo"), [], ["file.py", "data.txt"]),
            (os.path.normpath("/repo/subdir"), [], ["module.py", "readme.md"]),
            (os.path.normpath("/repo"), ["subdir2"], [])
        ]

    @pytest.fixture
    def translator(self):
        mock_config_loader = MagicMock(spec=ConfigLoader)
        mock_config_loader.config = MagicMock()
        mock_config_loader.config.git.repository = "https://github.com/example/repo"
        mock_config_loader.config.llm.api = "llama"

        translator = DirectoryTranslator(mock_config_loader)
        translator.model_handler = MagicMock(spec=ModelHandlerFactory.build(mock_config_loader.config))
        return translator

    def test_translate_text_excluded(self, translator):
        assert translator._translate_text("README") == "README"

    def test_translate_text(self, translator):
        translator.model_handler.send_request.return_value = "translated_text"
        assert translator._translate_text("тест") == "translated_text"

    @patch("os.walk")
    def test_get_python_files(self, mock_walk, mock_walk_data, translator):
        mock_walk.return_value = mock_walk_data
        result = translator._get_python_files()
        expected = [
            os.path.normpath("/repo/file.py"),
            os.path.normpath("/repo/subdir/module.py"),
        ]

        assert result == expected

    @patch("os.walk")
    def test_get_all_files(self, mock_walk, mock_walk_data, translator):
        mock_walk.return_value = mock_walk_data
        result = translator._get_all_files()

        assert len(result) == 4

    @patch("os.walk")
    def test_get_all_directories(self, mock_walk, mock_walk_data, translator):
        mock_walk.return_value = mock_walk_data
        result = translator._get_all_directories()
        expected = [os.path.normpath("/repo/subdir2")]

        assert result == expected

    @patch("os.rename")
    def test_rename_files(self, mock_rename, translator):
        with patch.object(translator, "_get_all_files", return_value=["/repo/file.txt"]), \
                patch.object(translator, "translate_files", return_value=(
                {"/repo/file.txt": "/repo/new_file.txt"}, {})):
            translator.rename_files()
        expected_call = tuple(os.path.normpath(path) for path in ("/repo/file.txt", "/repo/new_file.txt"))
        result_call = tuple(os.path.normpath(path) for path in mock_rename.call_args[0])

        assert result_call == expected_call

    @patch("os.rename")
    def test_rename_directories(self, mock_rename, translator):
        with patch.object(translator, "_get_all_directories", return_value=["/repo/old_dir"]), \
                patch.object(translator, "translate_directories", return_value={"old_dir": "new_dir"}):
            translator.rename_directories()
        expected_call = tuple(os.path.normpath(path) for path in ("/repo/old_dir", "/repo/new_dir"))
        result_call = tuple(os.path.normpath(path) for path in mock_rename.call_args[0])

        assert result_call == expected_call

    @patch("builtins.open", new_callable=mock_open, read_data="import os\nos.path.join('test')")
    @patch("os.path.exists", return_value=False)
    def test_update_code(self, mock_exists, mock_open, translator):
        translator.update_code("/repo/file.py", {"test": "translated_test"})
        mock_open.assert_called_with("/repo/file.py", "w", encoding="utf-8")

    @patch("builtins.open", new_callable=mock_open, read_data="import os")
    def test_update_code_with_invalid_regex(self, mock_open, translator):
        invalid_pattern = r"[a-zA-Z]+"
        translations = {invalid_pattern: "translated_text"}
        translator.update_code("/repo/file.py", translations)

        mock_open().write.assert_not_called()

    @pytest.mark.parametrize(
        "rename_map, input_code, expected_output",
        [
            (
                    {"os": "new_os", "sys": "new_sys"},
                    "import os\nimport sys\nfrom os.path import join",
                    "import new_os\nimport new_sys\nfrom new_os.path import join"
            ),
            (
                    {"folder": "new_folder", "file": "new_file"},
                    "os.path.join('folder', 'file')\nPath('folder/file')",
                    "os.path.join('new_folder', 'new_file')\nPath('new_folder/new_file')"
            ),
            (
                    {"folder": "new_folder"},
                    "shutil.copy('folder/file', 'folder/destination')",
                    "shutil.copy('new_folder/file', 'new_folder/destination')"
            ),
            (
                    {"folder": "new_folder"},
                    "glob.glob('folder/*.py')",
                    "glob.glob('new_folder/*.py')"
            ),
        ]
    )
    @patch("builtins.open", new_callable=mock_open)
    def test_update_code(
            self,
            mock_open,
            translator,
            rename_map,
            input_code,
            expected_output):
        mock_open.return_value.read.return_value = input_code
        translator.update_code("/repo/file.py", rename_map)

        mock_open.assert_called_with("/repo/file.py", "w", encoding="utf-8")
        mock_open().write.assert_called_with(expected_output)
