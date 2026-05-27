from pathlib import Path

import pytest

from osa_tool.operations.codebase.organization.organize import RepoOrganizer
from osa_tool.operations.codebase.organization.core.analyzers.generic import GenericReferenceAnalyzer
from osa_tool.operations.codebase.organization.core.analyzers.python import PythonImportAnalyzer
from osa_tool.operations.codebase.organization.core.executor.action_executor import (
    ActionExecutionError,
    ActionExecutor,
)
from osa_tool.operations.codebase.organization.core.executor.batch_updater import BatchImportUpdater


def test_repo_organizer_is_importable_from_new_package():
    assert RepoOrganizer.__name__ == "RepoOrganizer"


def test_python_import_key_uses_package_name_for_init_file(tmp_path: Path):
    analyzer = PythonImportAnalyzer(str(tmp_path))

    assert analyzer.get_import_key("pkg/__init__.py") == "pkg"
    assert analyzer.get_import_key("pkg/module.py") == "pkg.module"


def test_batch_updater_applies_multiple_replacements_to_same_file(tmp_path: Path):
    consumer = tmp_path / "consumer.py"
    consumer.write_text("from pkg.old_a import A\nimport pkg.old_b\n", encoding="utf-8")

    analyzer = PythonImportAnalyzer(str(tmp_path))
    analyzer.import_map = {
        "pkg.old_a": {"consumer.py"},
        "pkg.old_b": {"consumer.py"},
    }

    updater = BatchImportUpdater(tmp_path, {"python": analyzer})
    updater.add_move("pkg/old_a.py", "pkg/new_a.py")
    updater.add_move("pkg/old_b.py", "pkg/new_b.py")

    updater.apply_all()

    assert consumer.read_text(encoding="utf-8") == "from pkg.new_a import A\nimport pkg.new_b\n"


def test_generic_reference_analyzer_updates_quoted_and_unquoted_paths(tmp_path: Path):
    readme = tmp_path / "README.md"
    readme.write_text('See "docs/old.md" and docs/old.md for details.\n', encoding="utf-8")

    analyzer = GenericReferenceAnalyzer(str(tmp_path))

    updated = analyzer.update_imports_in_file("README.md", "docs/old.md", "docs/new.md")

    assert updated == 'See "docs/new.md" and docs/new.md for details.\n'


def test_action_executor_raises_on_missing_source_and_stops_following_actions(tmp_path: Path):
    executor = ActionExecutor(tmp_path, {})

    with pytest.raises(ActionExecutionError, match="Source file does not exist"):
        executor.execute_all(
            [
                {"type": "move_file", "source": "missing.py", "destination": "moved.py"},
                {"type": "create_file", "path": "should_not_exist.txt", "content": "blocked"},
            ]
        )

    assert not (tmp_path / "should_not_exist.txt").exists()
