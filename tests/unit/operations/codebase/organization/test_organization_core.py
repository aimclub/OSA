from pathlib import Path
from types import SimpleNamespace

import pytest

from osa_tool.operations.codebase.organization.core.health_checker import HealthChecker
from osa_tool.operations.codebase.organization.core.snapshot_manager import SnapshotManager
from osa_tool.operations.codebase.organization.organize import RepoOrganizer
from osa_tool.operations.codebase.organization.core.analyzers.generic import GenericReferenceAnalyzer
from osa_tool.operations.codebase.organization.core.analyzers.python import PythonImportAnalyzer
from osa_tool.operations.codebase.organization.core.executor.action_executor import (
    ActionExecutionError,
    ActionExecutor,
)
from osa_tool.operations.codebase.organization.core.executor.batch_updater import BatchImportUpdater
from osa_tool.operations.codebase.organization.core.planning_manager import PlanningManager


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


def test_validate_actions_rejects_existing_create_file_and_directory(tmp_path: Path):
    (tmp_path / ".gitignore").write_text("existing\n", encoding="utf-8")
    (tmp_path / "tests").mkdir()
    planner = PlanningManager(None, {}, tmp_path, "python")

    valid, issues = planner.validate_actions(
        [
            {"type": "create_file", "path": ".gitignore", "content": "new"},
            {"type": "create_directory", "path": "tests"},
        ]
    )

    assert not valid
    assert "File already exists: .gitignore" in issues
    assert "Directory already exists: tests" in issues


def test_validate_actions_rejects_protected_and_build_artifact_cleanup(tmp_path: Path):
    (tmp_path / "tox.ini").write_text("[tox]\n", encoding="utf-8")
    artifact_dir = tmp_path / "__pycache__"
    artifact_dir.mkdir()
    planner = PlanningManager(None, {}, tmp_path, "python")

    valid, issues = planner.validate_actions(
        [
            {"type": "delete_file", "path": "tox.ini"},
            {"type": "delete_directory", "path": "__pycache__"},
        ]
    )

    assert not valid
    assert "Protected path cannot be deleted: tox.ini" in issues
    assert "Build artifacts should be cleaned automatically, not deleted via plan: __pycache__" in issues


def test_validate_actions_allows_safe_python_module_extraction(tmp_path: Path):
    (tmp_path / "helpers.py").write_text("VALUE = 1\n", encoding="utf-8")
    planner = PlanningManager(None, {}, tmp_path, "python")

    valid, issues = planner.validate_actions(
        [
            {"type": "create_directory", "path": "pkg"},
            {"type": "move_file", "source": "helpers.py", "destination": "pkg/helpers.py"},
            {"type": "create_file", "path": "pkg/__init__.py", "content": ""},
        ]
    )

    assert valid, issues


def test_validate_actions_rejects_python_entrypoint_src_migration(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('run')\n", encoding="utf-8")
    planner = PlanningManager(None, {}, tmp_path, "python")

    valid, issues = planner.validate_actions(
        [
            {"type": "create_directory", "path": "src"},
            {"type": "move_file", "source": "main.py", "destination": "src/main.py"},
        ]
    )

    assert not valid
    assert any("Python entrypoint should not be moved into src/" in issue for issue in issues)


def test_repo_organizer_prefers_platform_metadata_for_kotlin(tmp_path: Path):
    (tmp_path / "build.gradle").write_text("plugins {}\n", encoding="utf-8")
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "Main.kt").write_text("fun main() = Unit\n", encoding="utf-8")

    organizer = RepoOrganizer.__new__(RepoOrganizer)
    organizer.base_path = tmp_path
    organizer.metadata = SimpleNamespace(
        language="Kotlin",
        languages=["Kotlin", "Java"],
        language_stats={"Kotlin": 80.0, "Java": 20.0},
    )

    assert organizer._detect_project_type() == "kotlin"


def test_repo_organizer_uses_cpp_metadata_for_cpp_python_repo(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "native.cpp").write_text("int main() { return 0; }\n", encoding="utf-8")
    (tmp_path / "native.hpp").write_text("#pragma once\n", encoding="utf-8")

    organizer = RepoOrganizer.__new__(RepoOrganizer)
    organizer.base_path = tmp_path
    organizer.metadata = SimpleNamespace(
        language="C++",
        languages=["C++", "Python"],
        language_stats={"C++": 70.0, "Python": 30.0},
    )

    assert organizer._detect_project_type() == "cpp"


def test_repo_organizer_platform_stats_override_local_files(tmp_path: Path):
    (tmp_path / "main.py").write_text("print('hello')\n", encoding="utf-8")
    (tmp_path / "helper.py").write_text("print('world')\n", encoding="utf-8")

    organizer = RepoOrganizer.__new__(RepoOrganizer)
    organizer.base_path = tmp_path
    organizer.metadata = SimpleNamespace(
        language="C++",
        languages=["C++", "Python"],
        language_stats={"C++": 95.0, "Python": 5.0},
    )

    assert organizer._detect_project_type() == "cpp"


def test_health_checker_skips_missing_toolchain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    checker = HealthChecker(tmp_path, "go", None, {})
    monkeypatch.setattr(checker, "_command_is_available", lambda command: False)

    assert checker.check_health() == (True, "")


def test_repo_organizer_detects_mixed_project_from_platform_language_stats(tmp_path: Path):
    organizer = RepoOrganizer.__new__(RepoOrganizer)
    organizer.base_path = tmp_path
    organizer.metadata = SimpleNamespace(
        language="C++",
        languages=["C++", "Python", "CSS"],
        language_stats={"C++": 7514.0, "Python": 5198.0, "CSS": 3438.0},
    )

    assert organizer._detect_project_type() == "mixed"


def test_repo_organizer_ignores_small_platform_language_noise(tmp_path: Path):
    organizer = RepoOrganizer.__new__(RepoOrganizer)
    organizer.base_path = tmp_path
    organizer.metadata = SimpleNamespace(
        language="Python",
        languages=["Python", "CSS"],
        language_stats={"Python": 91.0, "CSS": 9.0},
    )

    assert organizer._detect_project_type() == "python"


def test_repo_organizer_detects_cpp_from_ino_file_locally(tmp_path: Path):
    (tmp_path / "firmware.ino").write_text("void setup() {}\n", encoding="utf-8")

    organizer = RepoOrganizer.__new__(RepoOrganizer)
    organizer.base_path = tmp_path
    organizer.metadata = None

    assert organizer._detect_project_type() == "cpp"


def test_snapshot_manager_merges_using_resolved_temp_branch_head(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command[:3] == ["git", "rev-parse", "--verify"]:
            return SimpleNamespace(stdout="deadbeef\n", stderr="")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr("osa_tool.operations.codebase.organization.core.snapshot_manager.subprocess.run", fake_run)

    manager = SnapshotManager(tmp_path)
    manager.original_branch = "main"

    assert manager.transfer_changes() is True
    assert ["git", "merge", "--squash", "deadbeef"] in calls
