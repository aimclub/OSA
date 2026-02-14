import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from osa_tool.core.models.event import EventKind
from osa_tool.operations.codebase.requirements_generation.requirements_generation import RequirementsGenerator


@pytest.fixture
def mock_config():
    """Mock configuration manager."""
    config_manager = MagicMock()
    config_manager.get_git_settings.return_value.repository = "https://github.com/test/repo"
    config_manager.get_prompts.return_value.get.return_value = "Merge {old_requirements} and {new_requirements}"
    return config_manager


@pytest.fixture
def mock_plan():
    """Mock the scheduler plan."""
    return MagicMock()


@pytest.fixture
def generator(mock_config, mock_plan):
    """Create a generator instance with mocked dependencies."""
    with patch(
        "osa_tool.operations.codebase.requirements_generation.requirements_generation.ModelHandlerFactory.build"
    ):
        with patch(
            "osa_tool.operations.codebase.requirements_generation.requirements_generation.parse_folder_name",
            return_value="repo",
        ):
            gen = RequirementsGenerator(mock_config, mock_plan)
            gen.repo_path = MagicMock(spec=Path)
            gen.repo_path.resolve.return_value = gen.repo_path
            gen.repo_path.__str__.return_value = "/abs/path/to/repo"
            return gen


def test_clean_llm_response_simple(generator):
    raw = "pandas==1.0.0\nnumpy"
    cleaned = generator._clean_llm_response(raw)
    assert cleaned == "pandas==1.0.0\nnumpy"


def test_clean_llm_response_markdown(generator):
    raw = "```text\npandas==1.0.0\nnumpy\n```"
    cleaned = generator._clean_llm_response(raw)
    assert cleaned == "pandas==1.0.0\nnumpy"

    raw_2 = "```\npandas\n```"
    assert generator._clean_llm_response(raw_2) == "pandas"


def test_get_existing_context_both_files(generator):
    req_path = MagicMock()
    req_path.exists.return_value = True
    req_path.read_text.return_value = "old-reqs==1.0"

    pyproj_path = MagicMock()
    pyproj_path.exists.return_value = True
    pyproj_path.read_text.return_value = "[project] dependencies"

    context = generator._get_existing_context(req_path, pyproj_path)

    assert "--- EXISTING REQUIREMENTS.TXT ---" in context
    assert "old-reqs==1.0" in context
    assert "--- EXISTING PYPROJECT.TOML ---" in context
    assert "[project] dependencies" in context


def test_get_existing_context_none(generator):
    req_path = MagicMock()
    req_path.exists.return_value = False
    pyproj_path = MagicMock()
    pyproj_path.exists.return_value = False

    context = generator._get_existing_context(req_path, pyproj_path)
    assert context == ""


@patch("subprocess.run")
def test_run_pipreqs_success_first_try(mock_subprocess, generator):
    mock_subprocess.return_value = MagicMock(returncode=0)

    result = generator._run_pipreqs(scan_notebooks=True)

    assert result.returncode == 0
    cmd_args = mock_subprocess.call_args[0][0]
    assert "--scan-notebooks" in cmd_args


@patch("subprocess.run")
def test_run_pipreqs_fail(mock_subprocess, generator):
    mock_subprocess.side_effect = subprocess.CalledProcessError(1, "cmd", stderr="error")

    with pytest.raises(subprocess.CalledProcessError):
        generator._run_pipreqs(scan_notebooks=False)


@patch(
    "osa_tool.operations.codebase.requirements_generation.requirements_generation.RequirementsGenerator._run_pipreqs"
)
@patch(
    "osa_tool.operations.codebase.requirements_generation.requirements_generation.RequirementsGenerator._refine_with_llm"
)
def test_generate_success_simple(mock_refine, mock_run_pipreqs, generator):
    """
    Happy path: Repo exists, pipreqs works first time, context found -> LLM called.
    """
    generator.repo_path.exists.return_value = True

    req_file_mock = MagicMock()
    req_file_mock.exists.return_value = True
    req_file_mock.read_text.side_effect = ["old-lib==1.0", "new-lib"]
    req_file_mock.__str__.return_value = "requirements.txt"

    pyproj_mock = MagicMock()
    pyproj_mock.exists.return_value = False

    def path_div_side_effect(other):
        if other == "requirements.txt":
            return req_file_mock
        if other == "pyproject.toml":
            return pyproj_mock
        return MagicMock()

    generator.repo_path.__truediv__.side_effect = path_div_side_effect

    mock_run_pipreqs.return_value = MagicMock(returncode=0)

    # Act
    result = generator.generate()

    # Assert
    generator.plan.mark_started.assert_called_with("requirements")
    mock_run_pipreqs.assert_called_once_with(scan_notebooks=True)

    mock_refine.assert_called_once()

    generator.plan.mark_done.assert_called_with("requirements")
    assert result["result"]["path"].endswith("requirements.txt")


@patch(
    "osa_tool.operations.codebase.requirements_generation.requirements_generation.RequirementsGenerator._run_pipreqs"
)
def test_generate_retry_logic(mock_run_pipreqs, generator):
    """
    Scenario: Pipreqs fails with notebooks, retries without notebooks and succeeds.
    """
    generator.repo_path.exists.return_value = True

    # Mock file reading (no context)
    req_file = generator.repo_path / "requirements.txt"
    req_file.exists.return_value = False

    # Mock pipreqs
    mock_run_pipreqs.side_effect = [
        subprocess.CalledProcessError(1, "cmd", stderr="notebook error"),  # 1st call
        MagicMock(returncode=0),  # 2nd call
    ]

    # Act
    generator.generate()

    # Assert
    assert mock_run_pipreqs.call_count == 2
    assert mock_run_pipreqs.call_args_list[0] == call(scan_notebooks=True)
    assert mock_run_pipreqs.call_args_list[1] == call(scan_notebooks=False)

    assert len(generator.events) == 2
    assert generator.events[0].kind == EventKind.FAILED
    assert generator.events[0].data["mode"] == "scan-notebooks"
    assert generator.events[1].kind == EventKind.GENERATED
    assert generator.events[1].data["mode"] == "no-notebooks"


@patch(
    "osa_tool.operations.codebase.requirements_generation.requirements_generation.RequirementsGenerator._run_pipreqs"
)
def test_generate_fatal_failure(mock_run_pipreqs, generator):
    """Scenario: Pipreqs fails both times."""
    generator.repo_path.exists.return_value = True

    req_file_mock = MagicMock()
    pyproj_mock = MagicMock()
    generator.repo_path.__truediv__.side_effect = lambda x: req_file_mock if x == "requirements.txt" else pyproj_mock

    mock_run_pipreqs.side_effect = [
        subprocess.CalledProcessError(1, "cmd", stderr="err1"),
        subprocess.CalledProcessError(1, "cmd", stderr="err2"),
    ]

    # Act / Assert
    with pytest.raises(subprocess.CalledProcessError):
        generator.generate()

    generator.plan.mark_failed.assert_called_with("requirements")

    assert len(generator.events) == 2
    assert generator.events[1].kind == EventKind.FAILED
    assert generator.events[1].data["mode"] == "no-notebooks"


def test_refine_with_llm_writes_file(generator):
    """Test that _refine_with_llm actually writes to the file."""
    # Setup
    req_path = MagicMock()
    req_path.read_text.return_value = "new-lib"
    old_context = "old-lib==1.0"

    generator.model_handler.send_request.return_value = "merged-lib==1.0"

    # Act
    generator._refine_with_llm(req_path, old_context)

    # Assert
    generator.model_handler.send_request.assert_called_once()
    req_path.write_text.assert_called_once_with("merged-lib==1.0", encoding="utf-8")
    assert generator.events[-1].kind == EventKind.REFINED


def test_run_pipreqs_subprocess(generator):
    """Test actual subprocess call composition."""
    with patch("subprocess.run") as mock_sp:
        mock_sp.return_value = MagicMock(stdout="ok")

        # Test True
        generator._run_pipreqs(scan_notebooks=True)
        args_true = mock_sp.call_args[0][0]
        assert "--scan-notebooks" in args_true
        assert "--force" in args_true

        # Test False
        generator._run_pipreqs(scan_notebooks=False)
        args_false = mock_sp.call_args[0][0]
        assert "--scan-notebooks" not in args_false
        assert str(generator.repo_path) in args_false
