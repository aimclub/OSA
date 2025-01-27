from pathlib import Path
from typing import Any

import pytest

from readmeai.preprocessor.file_filter import is_excluded, is_included


@pytest.fixture
def repo_path() -> Path:
    return Path("/home/user/project")


class TestExcludedList:
    @pytest.fixture
    def ignore_list(self) -> dict[str, Any]:
        return {
            "directories": ["node_modules", ".git"],
            "extensions": ["pyc", "tmp"],
            "files": [".DS_Store", "Thumbs.db"],
        }

    @pytest.mark.parametrize(
        "file_path,expected",
        [
            (Path("/home/user/project/src/main.py"), False),
            (Path("/home/user/project/node_modules/package.json"), True),
            (Path("/home/user/project/.git/config"), True),
            (Path("/home/user/project/build/output.pyc"), True),
            (Path("/home/user/project/temp.tmp"), True),
            (Path("/home/user/project/.DS_Store"), True),
            (Path("/home/user/project/docs/Thumbs.db"), True),
            (Path("/home/user/project/src/utils.py"), False),
        ],
    )
    def test_is_excluded(
            self,
            file_path: Path,
            expected: bool,
            repo_path: Path,
            ignore_list: dict[str, Any],
    ) -> None:
        assert is_excluded(ignore_list, file_path, repo_path) == expected

    def test_is_excluded_empty_ignore_list(
            self,
            repo_path:
            Path
    ):
        empty_ignore_list = {"directories": [], "extensions": [], "files": []}
        file_path = Path("/home/user/project/src/main.py")
        assert not is_excluded(empty_ignore_list, file_path, repo_path)

    def test_is_excluded_no_match(
            self,
            repo_path: Path,
            ignore_list: dict[str, Any],
    ):
        file_path = Path("/home/user/project/src/app.js")
        assert not is_excluded(ignore_list, file_path, repo_path)

    def test_is_excluded_case_sensitivity(
            self,
            repo_path: Path,
            ignore_list: dict[str, Any]
    ):
        file_path = Path("/home/user/project/.GIT/config")
        assert not is_excluded(ignore_list, file_path, repo_path)

    def test_is_excluded_nested_directory(
            self,
            repo_path: Path,
            ignore_list: dict[str, Any]
    ):
        file_path = Path("/home/user/project/src/node_modules/package.json")
        assert is_excluded(ignore_list, file_path, repo_path)


class TestIncludedList:
    @pytest.fixture
    def docs_list(self) -> dict[str, Any]:
        return {
            "directories": ["docs", "tutorials"],
            "extensions": ["md", "rst"],
            "files": ["LICENSE", "CITATION.cff"],
        }

    @pytest.mark.parametrize(
        "file_path,expected",
        [
            (Path("/home/user/project/src/main.py"), False),
            (Path("/home/user/project/docs/examples"), True),
            (Path("/home/user/project/.git/config"), False),
            (Path("/home/user/project/examples/tutorials"), True),
            (Path("/home/user/project/README.md"), True),
            (Path("/home/user/project/LICENSE"), True),
            (Path("/home/user/project/docs/CITATION.cff"), True),
            (Path("/home/user/project/src/README.rst"), True),
        ],
    )
    def test_is_included(
            self,
            file_path: Path,
            expected: bool,
            repo_path: Path,
            docs_list: dict[str, Any],
    ) -> None:
        assert is_included(docs_list, file_path, repo_path) == expected

    def test_is_included_empty_docs_list(
            self,
            repo_path: Path,
    ):
        empty_docs_list = {"directories": [], "extensions": [], "files": []}
        file_path = Path("/home/user/project/src/main.py")
        assert not is_included(empty_docs_list, file_path, repo_path)

    def test_is_included_no_match(
            self,
            repo_path: Path,
            docs_list: dict[str, Any],
    ):
        file_path = Path("/home/user/project/examples/example_1.py")
        assert not is_excluded(docs_list, file_path, repo_path)

    def test_is_included_case_sensitivity(
            self,
            repo_path: Path,
            docs_list: dict[str, Any],
    ):
        file_path = Path("/home/user/project/DOCS/file1.txt")
        assert not is_excluded(docs_list, file_path, repo_path)

    def test_is_included_nested_directory(
            self,
            repo_path: Path,
            docs_list: dict[str, Any],
    ):
        file_path = Path("/home/user/project/src/tutorials/package.json")
        assert is_excluded(docs_list, file_path, repo_path)
