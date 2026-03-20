import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from osa_tool.core.models.event import EventKind
from osa_tool.operations.codebase.requirements_generation.requirements_generation import (
    RequirementsGenerator,
    MergedRequirements,
)


@pytest.fixture
def mock_config():
    """
    Mock configuration manager for testing purposes.
    
    This function creates a MagicMock object that simulates the behavior of a configuration manager. It is used to provide consistent mock responses for configuration-related methods during unit tests, avoiding dependencies on actual configuration files or external services.
    
    Args:
        None.
    
    Returns:
        A MagicMock object configured with predefined return values for:
        - `get_git_settings().repository`: Returns a test repository URL.
        - `get_prompts().get()`: Returns a string template for merging requirements.
    
    Example of typical usage in tests:
        The mock is set up so that `config_manager.get_git_settings().repository` yields "https://github.com/test/repo" and `config_manager.get_prompts().get()` yields "Merge {old_requirements} and {new_requirements}".
    """
    config_manager = MagicMock()
    config_manager.get_git_settings.return_value.repository = "https://github.com/test/repo"
    config_manager.get_prompts.return_value.get.return_value = "Merge {old_requirements} and {new_requirements}"
    return config_manager


@pytest.fixture
def generator(mock_config):
    """
    Create a RequirementsGenerator instance with mocked dependencies for testing.
    
    This method is used in unit tests to instantiate a RequirementsGenerator with its external dependencies patched, ensuring tests run in isolation without relying on actual filesystem paths or model-handling logic. It mocks the ModelHandlerFactory.build method to prevent real model initialization and patches parse_folder_name to return a fixed string, while also setting up a mocked repo_path with predefined behavior.
    
    Args:
        mock_config: The configuration object to pass to the RequirementsGenerator constructor.
    
    Returns:
        A RequirementsGenerator instance with mocked repo_path and patched external dependencies.
    """
    with patch(
        "osa_tool.operations.codebase.requirements_generation.requirements_generation.ModelHandlerFactory.build"
    ):
        with patch(
            "osa_tool.operations.codebase.requirements_generation.requirements_generation.parse_folder_name",
            return_value="repo",
        ):
            gen = RequirementsGenerator(mock_config)
            gen.repo_path = MagicMock(spec=Path)
            gen.repo_path.resolve.return_value = gen.repo_path
            gen.repo_path.__str__.return_value = "/abs/path/to/repo"
            return gen


def test_get_existing_context_both_files(generator):
    """
    Verifies that the context generator correctly retrieves and formats content from both requirements.txt and pyproject.toml when both files exist.
    
    This test ensures that when both dependency files are present, the generator combines their contents into a single formatted context string, preserving the original dependency information for later use.
    
    Args:
        generator: The RequirementsGenerator instance being tested. It provides the _get_existing_context method, which reads and formats the existing dependency files.
    
    Returns:
        None.
    """
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
    """
    Verifies that _get_existing_context returns an empty string when neither the requirements file nor the pyproject.toml file exists.
    
    This test ensures that the method correctly handles the scenario where no dependency files are present, returning an empty context to indicate no existing dependencies to preserve.
    
    Args:
        generator: The RequirementsGenerator instance being tested.
    
    Returns:
        None.
    """
    req_path = MagicMock()
    req_path.exists.return_value = False
    pyproj_path = MagicMock()
    pyproj_path.exists.return_value = False

    context = generator._get_existing_context(req_path, pyproj_path)
    assert context == ""


@patch("subprocess.run")
def test_run_pipreqs_success_first_try(mock_subprocess, generator):
    """
    Tests that the _run_pipreqs method successfully executes on the first attempt.
    
    This test verifies that when pipreqs runs without error (returncode 0), the method
    returns the expected result and includes the correct command-line argument for
    notebook scanning when requested.
    
    Args:
        mock_subprocess: A mock object representing the subprocess.run function.
        generator: An instance of the RequirementsGenerator class being tested.
    
    Returns:
        None.
    """
    mock_subprocess.return_value = MagicMock(returncode=0)

    result = generator._run_pipreqs(scan_notebooks=True)

    assert result.returncode == 0
    cmd_args = mock_subprocess.call_args[0][0]
    assert "--scan-notebooks" in cmd_args


@patch("subprocess.run")
def test_run_pipreqs_fail(mock_subprocess, generator):
    """
    Tests that _run_pipreqs raises a subprocess.CalledProcessError when the underlying command fails.
    
    This test ensures that the method properly propagates failures from the pipreqs subprocess.
    
    Args:
        mock_subprocess: A mock object representing the subprocess.run function.
        generator: An instance of the RequirementsGenerator class being tested.
    
    Raises:
        subprocess.CalledProcessError: Expected when the pipreqs command execution returns a non-zero exit code.
    """
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
    Tests the successful generation of requirements via the happy path scenario.
    
    This test simulates the ideal case where:
    1. The repository exists.
    2. The `pipreqs` command runs successfully on the first attempt.
    3. A requirements file is found in the repository.
    4. The LLM refinement step is subsequently called.
    
    WHY: This test validates the core, error-free workflow of the requirements generation process,
    ensuring that when all preconditions are met and external tools succeed, the method correctly
    executes the full pipeline and returns the expected result.
    
    Args:
        mock_refine: Mock of the `_refine_with_llm` method.
        mock_run_pipreqs: Mock of the `_run_pipreqs` method.
        generator: The RequirementsGenerator instance under test.
    
    Returns:
        None. This is a test method; assertions are made within the body.
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
    mock_run_pipreqs.assert_called_once_with(scan_notebooks=True)

    mock_refine.assert_called_once()

    assert result["result"]["path"].endswith("requirements.txt")


@patch(
    "osa_tool.operations.codebase.requirements_generation.requirements_generation.RequirementsGenerator._run_pipreqs"
)
def test_generate_retry_logic(mock_run_pipreqs, generator):
    """
    Test the retry logic in requirements generation when pipreqs fails due to notebook processing.
    
    This test verifies that if `pipreqs` fails while scanning notebooks, the generator will
    retry the operation without scanning notebooks and succeed. It ensures the retry mechanism
    works correctly and that appropriate events are recorded for each attempt.
    
    Args:
        mock_run_pipreqs: Mock of the internal `_run_pipreqs` method, used to simulate pipreqs failures and successes.
        generator: An instance of the RequirementsGenerator fixture, configured for testing.
    
    The test sets up a scenario where:
    1. The first call to `_run_pipreqs` (with `scan_notebooks=True`) raises a subprocess error.
    2. The second call (with `scan_notebooks=False`) completes successfully.
    It then validates that:
    - `_run_pipreqs` is called exactly twice, with the expected arguments.
    - Two events are recorded: a FAILED event for the notebook‑scan attempt and a GENERATED event for the no‑notebook attempt.
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
    """
    Test the scenario where pipreqs fails in both attempts during requirements generation.
    
    This test verifies that the generator correctly handles a fatal failure when pipreqs cannot produce a requirements.txt file. It simulates two consecutive subprocess errors and ensures the generator raises the appropriate exception and logs failure events.
    
    Args:
        mock_run_pipreqs: Mocked method for running pipreqs, configured to raise CalledProcessError twice.
        generator: The RequirementsGenerator instance under test, with mocked repository path and file objects.
    
    Why:
        This test ensures the generator does not silently ignore repeated pipreqs failures and properly propagates the error, while also recording the failure event for monitoring or logging purposes.
    """
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

    assert len(generator.events) == 3
    assert generator.events[2].kind == EventKind.FAILED
    assert generator.events[2].data["mode"] == "no-notebooks"


def test_refine_with_llm_writes_file(generator):
    """
    Test that _refine_with_llm writes the merged dependencies to the requirements file and logs an event.
    
    This test verifies that the `_refine_with_llm` method correctly processes a requirements file by:
    1. Reading the existing requirements content.
    2. Sending the content to the LLM for merging and parsing.
    3. Writing the LLM's merged dependency list back to the file.
    4. Recording a refinement event.
    
    Args:
        generator: A test fixture providing a RequirementsGenerator instance with mocked dependencies.
    
    The test uses mocked objects to simulate file reading and LLM responses, ensuring that the file is written with the correct merged content and that an event of kind `EventKind.REFINED` is appended to the generator's events list.
    """
    # Setup
    req_path = MagicMock()
    req_path.read_text.return_value = "new-lib"
    old_context = "old-lib==1.0"

    mock_response = MergedRequirements(dependencies=["merged-lib==1.0", "numpy"])
    generator.model_handler.send_and_parse.return_value = mock_response

    # Act
    generator._refine_with_llm(req_path, old_context)

    # Assert
    generator.model_handler.send_and_parse.assert_called_once()
    req_path.write_text.assert_called_once_with("merged-lib==1.0\nnumpy", encoding="utf-8")
    assert generator.events[-1].kind == EventKind.REFINED


def test_run_pipreqs_subprocess(generator):
    """
    Test actual subprocess call composition for pipreqs execution.
    
    This test verifies that the `_run_pipreqs` helper method correctly constructs the subprocess command arguments based on the `scan_notebooks` parameter. It ensures that the `--scan-notebooks` flag is included when `scan_notebooks=True` and omitted when `scan_notebooks=False`, and that the `--force` flag and repository path are properly included in the command.
    
    Args:
        generator: A test fixture or instance providing the `_run_pipreqs` method and `repo_path` attribute.
    
    The test uses mocking to intercept the subprocess call and inspect the constructed arguments without actually running pipreqs.
    """
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
