from unittest.mock import MagicMock, patch

from osa_tool.core.models.llm_output_models import LlmTextOutput
from osa_tool.operations.docs.readme_generation.llm_schemas import KeyFilesLLMOutput
from osa_tool.operations.docs.readme_generation.agent.nodes.context_collector import (
    _compute_budgets,
    _read_files_with_budget,
    _truncate_tree,
    context_collector_node,
)
from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState


def test_compute_budgets_standard_context_window():
    # Arrange
    available = 16385 - 4096 - 200

    # Act
    budgets = _compute_budgets(context_window=16385, max_output_tokens=4096)

    # Assert
    assert budgets["tree"] == min(4000, int(available * 0.30))
    assert budgets["key_files"] == min(6000, int(available * 0.40))
    assert budgets["existing_readme"] == min(4000, int(available * 0.25))
    assert budgets["examples"] == min(2000, int(available * 0.10))
    assert budgets["pdf"] == min(3000, int(available * 0.20))


def test_compute_budgets_large_context_window_caps_apply():
    # Act
    budgets = _compute_budgets(context_window=200_000, max_output_tokens=4096)

    # Assert
    assert budgets["tree"] <= 4000
    assert budgets["key_files"] <= 6000
    assert budgets["existing_readme"] <= 4000
    assert budgets["examples"] <= 2000
    assert budgets["pdf"] <= 3000


def test_compute_budgets_tiny_context_window_floors_to_minimum():
    # Act
    budgets = _compute_budgets(context_window=500, max_output_tokens=400)

    # Assert
    assert all(v > 0 for v in budgets.values())


def test_truncate_tree_short_tree_unchanged():
    # Arrange
    tree = "README.md\nsrc\nsrc/main.py\ntests\ntests/test_main.py"

    # Act
    result = _truncate_tree(tree, max_tokens=5000, encoding_name="cl100k_base")

    # Assert
    assert result == tree


def test_truncate_tree_empty():
    # Act
    out = _truncate_tree("", max_tokens=100, encoding_name="cl100k_base")

    # Assert
    assert out == ""


def test_truncate_tree_preserves_shallow_entries():
    # Arrange
    lines = [
        "README.md",
        "src",
        "src/core",
        "src/core/engine.py",
        "src/core/utils/helpers.py",
        "src/core/utils/__init__.py",
    ]
    tree = "\n".join(lines)

    # Act
    result = _truncate_tree(tree, max_tokens=1, encoding_name="cl100k_base")

    # Assert
    assert isinstance(result, str)


def test_truncate_tree_prunes_deep_non_important_files():
    # Arrange
    lines = [
        "README.md",
        "src",
        "src/core",
        "src/core/engine.py",
        "src/core/deep/nested/random_module.py",
        "src/core/deep/nested/__init__.py",
    ]
    tree = "\n".join(lines)

    # Act
    with patch(
        "osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.count_tokens",
        side_effect=[999, 5],
    ):
        result = _truncate_tree(tree, max_tokens=10, encoding_name="cl100k_base")

    # Assert
    assert "random_module.py" not in result
    assert "__init__.py" in result


@patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.read_file")
@patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.count_tokens")
@patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.truncate_to_tokens")
def test_read_files_with_budget_reads_in_priority_order(mock_truncate, mock_count, mock_read):
    # Arrange
    mock_read.side_effect = ["content_a", "content_b", "content_c"]
    mock_truncate.side_effect = ["content_a", "content_b", "content_c"]
    mock_count.side_effect = [100, 100, 100]

    # Act
    paths, serialized = _read_files_with_budget(
        "/repo",
        ["a.py", "b.py", "c.py"],
        total_budget=300,
        per_file_cap=200,
        encoding_name="cl100k_base",
    )

    # Assert
    assert paths == ["a.py", "b.py", "c.py"]
    assert "a.py" in serialized
    assert "b.py" in serialized
    assert "c.py" in serialized


@patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.read_file")
@patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.count_tokens")
@patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.truncate_to_tokens")
def test_read_files_with_budget_stops_when_budget_exhausted(mock_truncate, mock_count, mock_read):
    # Arrange
    mock_read.side_effect = ["content_a", "content_b", "content_c"]
    mock_truncate.side_effect = ["content_a", "content_b"]
    mock_count.side_effect = [150, 150]

    # Act
    paths, _ = _read_files_with_budget(
        "/repo",
        ["a.py", "b.py", "c.py"],
        total_budget=200,
        per_file_cap=200,
        encoding_name="cl100k_base",
    )

    # Assert
    assert len(paths) <= 2


@patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.read_file")
def test_read_files_with_budget_skips_empty_files(mock_read):
    # Arrange
    mock_read.side_effect = ["", "real content"]

    # Act
    with (
        patch(
            "osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.truncate_to_tokens",
            return_value="real content",
        ),
        patch(
            "osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.count_tokens",
            return_value=10,
        ),
    ):
        paths, _ = _read_files_with_budget(
            "/repo",
            ["empty.py", "real.py"],
            total_budget=1000,
            per_file_cap=500,
            encoding_name="cl100k_base",
        )

    # Assert
    assert paths == ["real.py"]


def test_read_files_with_budget_empty_file_list():
    # Act
    paths, content = _read_files_with_budget(
        "/repo",
        [],
        total_budget=1000,
        per_file_cap=500,
        encoding_name="cl100k_base",
    )

    # Assert
    assert paths == []
    assert content == ""


def test_read_files_with_budget_zero_budget():
    # Act
    paths, content = _read_files_with_budget(
        "/repo",
        ["a.py"],
        total_budget=0,
        per_file_cap=500,
        encoding_name="cl100k_base",
    )

    # Assert
    assert paths == []
    assert content == ""


@patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.SourceRank")
@patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.extract_readme_content")
@patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.extract_example_paths")
@patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.read_file")
@patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector._run_parallel_analyses")
def test_context_collector_node_returns_all_expected_keys(
    mock_parallel,
    mock_read_file,
    mock_examples,
    mock_extract_readme,
    mock_sourcerank_cls,
    mock_config_manager,
    mock_repository_metadata,
):
    # Arrange
    mock_sourcerank_cls.return_value.tree = "README.md\nsrc\nsrc/main.py"
    mock_extract_readme.return_value = "# Test Project"
    mock_examples.return_value = []
    mock_read_file.return_value = "print('hello')"
    mock_parallel.return_value = ("readme analysis result", None)

    mock_model_handler = MagicMock()
    mock_model_handler.send_and_parse.side_effect = [
        KeyFilesLLMOutput(key_files=["src/main.py"]),
        LlmTextOutput(text="repo analysis result"),
    ]

    mock_context = MagicMock()
    mock_context.config_manager = mock_config_manager
    mock_context.model_handler = mock_model_handler
    mock_context.prompts = mock_config_manager.get_prompts()
    mock_context.metadata = mock_repository_metadata

    state = ReadmeState(repo_url="https://github.com/test/repo")

    # Act
    result = context_collector_node(state, mock_context)

    # Assert
    expected_keys = {
        "repo_tree",
        "existing_readme",
        "key_files",
        "key_files_content",
        "examples_content",
        "pdf_content",
        "repo_analysis",
        "readme_analysis",
        "article_analysis",
    }
    assert set(result.keys()) == expected_keys
    assert result["repo_analysis"] == "repo analysis result"
    assert result["readme_analysis"] == "readme analysis result"
    assert result["pdf_content"] is None
    assert result["article_analysis"] is None
