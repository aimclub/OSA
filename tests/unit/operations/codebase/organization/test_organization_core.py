from pathlib import Path
from types import SimpleNamespace
import logging
import subprocess

import pytest

from osa_tool.operations.codebase.organization.core.health_checker import HealthChecker
from osa_tool.operations.codebase.organization.core.snapshot_manager import SnapshotManager
from osa_tool.operations.codebase.organization.organize import RepoOrganizer
from osa_tool.operations.codebase.organization.core.analyzers.generic import GenericReferenceAnalyzer
from osa_tool.operations.codebase.organization.core.analyzers.javascript import JavaScriptImportAnalyzer
from osa_tool.operations.codebase.organization.core.analyzers.python import PythonImportAnalyzer
from osa_tool.operations.codebase.organization.core.executor.action_executor import (
    ActionExecutionError,
    ActionExecutor,
)
from osa_tool.operations.codebase.organization.core.executor.batch_updater import BatchImportUpdater
from osa_tool.operations.codebase.organization.core.planning_manager import PlanningManager
from osa_tool.operations.codebase.organization import organize as organize_module


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


def test_batch_updater_updates_generic_references_for_moved_python_file(tmp_path: Path):
    consumer = tmp_path / "README.md"
    consumer.write_text("Use pkg/old.py in docs.\n", encoding="utf-8")
    moved_file = tmp_path / "pkg" / "old.py"
    moved_file.parent.mkdir()
    moved_file.write_text("VALUE = 1\n", encoding="utf-8")

    python_analyzer = PythonImportAnalyzer(str(tmp_path))
    generic_analyzer = GenericReferenceAnalyzer(str(tmp_path), excluded_extensions={".py"})
    generic_analyzer.import_map = {"pkg/old.py": {"README.md"}}

    updater = BatchImportUpdater(tmp_path, {"python": python_analyzer, "generic": generic_analyzer})
    updater.add_move("pkg/old.py", "pkg/new.py")
    updater.apply_all()

    assert consumer.read_text(encoding="utf-8") == "Use pkg/new.py in docs.\n"


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


def test_action_executor_rejects_paths_outside_repository(tmp_path: Path):
    executor = ActionExecutor(tmp_path, {})

    with pytest.raises(ActionExecutionError, match="Path escapes repository"):
        executor.execute_all([{"type": "create_file", "path": "../outside.txt", "content": "blocked"}])


def test_action_executor_rejects_delete_actions(tmp_path: Path):
    executor = ActionExecutor(tmp_path, {})

    with pytest.raises(ActionExecutionError, match="Delete actions are disabled during reorganization"):
        executor.execute_all([{"type": "delete_file", "path": "obsolete.txt"}])


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
    assert (
        "Delete actions are not allowed during reorganization; move or quarantine the file instead: tox.ini" in issues
    )
    assert (
        "Delete actions are not allowed during reorganization; move or quarantine the directory instead: __pycache__"
        in issues
    )


def test_validate_actions_logs_manual_review_for_secret_like_delete(tmp_path: Path, caplog: pytest.LogCaptureFixture):
    planner = PlanningManager(None, {}, tmp_path, "python")

    with caplog.at_level(logging.WARNING):
        valid, issues = planner.validate_actions([{"type": "delete_file", "path": ".env.secret"}])

    assert not valid
    assert (
        "Delete actions are not allowed during reorganization; move or quarantine the file instead: .env.secret"
        in issues
    )
    assert "potentially sensitive file '.env.secret'" in caplog.text


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


def test_python_analyzer_updates_relative_imports_after_move(tmp_path: Path):
    package = tmp_path / "pkg"
    package.mkdir()
    consumer = package / "consumer.py"
    consumer.write_text("from .foo import Bar\n", encoding="utf-8")

    analyzer = PythonImportAnalyzer(str(tmp_path))
    analyzer.import_map = {"pkg.foo": {"pkg/consumer.py"}}

    updater = BatchImportUpdater(tmp_path, {"python": analyzer})
    updater.add_move("pkg/foo.py", "pkg/sub/foo.py")
    updater.apply_all()

    assert consumer.read_text(encoding="utf-8") == "from .sub.foo import Bar\n"


def test_health_checker_skips_missing_toolchain(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    checker = HealthChecker(tmp_path, "go", None, {})
    monkeypatch.setattr(checker, "_command_is_available", lambda command: False)

    assert checker.check_health() == (True, "")


def test_health_checker_runs_python_and_js_fallbacks_for_mixed_projects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    (tmp_path / "broken.py").write_text("if True print('oops')\n", encoding="utf-8")
    (tmp_path / "broken.js").write_text("function () {\n", encoding="utf-8")

    checker = HealthChecker(tmp_path, "mixed", None, {})

    def fake_run(command, cwd=None):
        joined = " ".join(command)
        if "py_compile" in joined:
            return 1, "", "python syntax error"
        if command[:2] == ["node", "--check"]:
            return 1, "", "js syntax error"
        return 0, "", ""

    monkeypatch.setattr(checker, "_run_command", fake_run)

    healthy, errors = checker.check_health()

    assert healthy is False
    assert "broken.py" in errors
    assert "broken.js" in errors


def test_health_checker_runs_typescript_fallback_for_mixed_projects(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    (tmp_path / "broken.ts").write_text("const x: string = 1;\n", encoding="utf-8")

    checker = HealthChecker(tmp_path, "mixed", None, {})

    def fake_run(command, cwd=None):
        if command[:2] == ["npx", "tsc"]:
            return 1, "", "broken.ts: Type 'number' is not assignable to type 'string'"
        return 0, "", ""

    monkeypatch.setattr(checker, "_run_command", fake_run)

    healthy, errors = checker.check_health()

    assert healthy is False
    assert "broken.ts" in errors


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


def test_snapshot_manager_restores_preserved_local_changes_on_rollback(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command == ["git", "branch", "--show-current"]:
            return SimpleNamespace(stdout="main\n", stderr="")
        if command == ["git", "status", "--porcelain"]:
            return SimpleNamespace(stdout=" M file.py\n", stderr="")
        if command == ["git", "stash", "list", "--format=%gd", "-n", "1"]:
            return SimpleNamespace(stdout="stash@{0}\n", stderr="")
        if command[:3] == ["git", "rev-parse", "--verify"]:
            return SimpleNamespace(stdout="deadbeef\n", stderr="")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr("osa_tool.operations.codebase.organization.core.snapshot_manager.subprocess.run", fake_run)

    manager = SnapshotManager(tmp_path)

    assert manager.create_snapshot() is True
    assert manager.rollback() is True
    assert ["git", "stash", "push", "--include-untracked", "-m", "OSA Tool: preserved local changes"] in calls
    assert ["git", "stash", "apply", "stash@{0}"] in calls
    assert ["git", "stash", "pop", "stash@{0}"] in calls


def test_snapshot_manager_restores_stash_when_snapshot_creation_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(command)
        if command == ["git", "branch", "--show-current"]:
            return SimpleNamespace(stdout="main\n", stderr="")
        if command == ["git", "status", "--porcelain"]:
            return SimpleNamespace(stdout=" M file.py\n", stderr="")
        if command == ["git", "stash", "list", "--format=%gd", "-n", "1"]:
            return SimpleNamespace(stdout="stash@{0}\n", stderr="")
        if command == [
            "git",
            "checkout",
            "-b",
            "osa-temp-" + SnapshotManager(tmp_path).temp_branch.split("osa-temp-")[1]
        ]:
            raise subprocess.CalledProcessError(returncode=1, cmd=command, stderr="checkout failed")
        if command[:3] == ["git", "checkout", "-b"]:
            raise subprocess.CalledProcessError(returncode=1, cmd=command, stderr="checkout failed")
        return SimpleNamespace(stdout="", stderr="")

    monkeypatch.setattr("osa_tool.operations.codebase.organization.core.snapshot_manager.subprocess.run", fake_run)

    manager = SnapshotManager(tmp_path)

    assert manager.create_snapshot() is False
    assert ["git", "stash", "push", "--include-untracked", "-m", "OSA Tool: preserved local changes"] in calls
    assert ["git", "stash", "pop", "stash@{0}"] in calls


def test_javascript_analyzer_preserves_relative_extension_when_updating_import(tmp_path: Path):
    consumer = tmp_path / "src" / "main.js"
    consumer.parent.mkdir(parents=True)
    consumer.write_text('import value from "./utils/foo.js";\n', encoding="utf-8")

    analyzer = JavaScriptImportAnalyzer(str(tmp_path))
    updated = analyzer.update_imports_in_file("src/main.js", "src/utils/foo", "src/lib/bar")

    assert updated == 'import value from "./lib/bar.js";\n'


def test_repo_organizer_does_not_delete_tracked_dist_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    organizer = RepoOrganizer.__new__(RepoOrganizer)
    organizer.base_path = tmp_path
    tracked_dist = tmp_path / "dist"
    tracked_dist.mkdir()
    (tracked_dist / "bundle.js").write_text("console.log('tracked');\n", encoding="utf-8")

    monkeypatch.setattr(organizer, "_is_git_tracked", lambda rel_path: rel_path.startswith("dist"))

    assert organizer._clean_pycache() is True
    assert tracked_dist.exists()


def test_repo_organizer_cleans_build_artifacts_again_before_post_health_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    calls = []

    class DummyExecutor:
        def __init__(self, base_path, analyzers):
            self.base_path = base_path
            self.analyzers = analyzers

        def execute_all(self, actions):
            calls.append(("execute_all", actions))

    organizer = RepoOrganizer.__new__(RepoOrganizer)
    organizer.repo_name = "demo"
    organizer.project_type = "python"
    organizer.base_path = tmp_path
    organizer.skip_health_check = False
    organizer.analyzers = {}
    organizer._build_import_maps = lambda: calls.append("build_import_maps")
    organizer._clean_pycache = lambda: calls.append("clean_pycache")
    organizer._commit_temp_branch_changes = lambda message: calls.append(("commit", message)) or True
    organizer._run_health_phase = lambda label: calls.append(("health", label)) or True
    organizer.planning = SimpleNamespace(
        generate_plan=lambda tree, repo_name: {"actions": []},
        validate_actions=lambda actions: (True, []),
        reorder_actions=lambda actions: actions,
    )
    organizer.snapshot = SimpleNamespace(
        create_snapshot=lambda: True,
        rollback=lambda: True,
        transfer_changes=lambda: True,
        temp_branch="osa-temp-123",
    )

    monkeypatch.setattr(organize_module, "ActionExecutor", DummyExecutor)

    organizer.organize()

    post_health_index = calls.index(("health", "PHASE 6: Post-reorganization health check"))
    post_health_commit_index = calls.index(("commit", "OSA Tool: post-health fixes"))
    final_cleanup_index = max(index for index, entry in enumerate(calls) if entry == "clean_pycache")

    assert post_health_index < final_cleanup_index
    assert final_cleanup_index < post_health_commit_index
