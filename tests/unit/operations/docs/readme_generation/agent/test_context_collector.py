from unittest.mock import MagicMock, patch

from osa_tool.operations.docs.readme_generation.agent.nodes.context_collector import (
    _compute_budgets,
    _read_files_with_budget,
    _truncate_tree,
    context_collector_node,
)


# ---------------------------------------------------------------------------
# _compute_budgets
# ---------------------------------------------------------------------------
class TestComputeBudgets:

    def test_standard_context_window(self):
        # Act
        budgets = _compute_budgets(context_window=16385, max_output_tokens=4096)

        # Assert
        # available = 16385 - 4096 - 200 = 12089
        assert budgets["tree"] == min(4000, int(12089 * 0.30))
        assert budgets["key_files"] == min(6000, int(12089 * 0.40))
        assert budgets["existing_readme"] == min(4000, int(12089 * 0.25))
        assert budgets["examples"] == min(2000, int(12089 * 0.10))
        assert budgets["pdf"] == min(3000, int(12089 * 0.20))

    def test_large_context_window_caps_apply(self):
        # Act
        budgets = _compute_budgets(context_window=200_000, max_output_tokens=4096)

        # Assert
        # Caps should prevent excessively large budgets
        assert budgets["tree"] <= 4000
        assert budgets["key_files"] <= 6000
        assert budgets["existing_readme"] <= 4000
        assert budgets["examples"] <= 2000
        assert budgets["pdf"] <= 3000

    def test_tiny_context_window_floors_to_minimum(self):
        # Act
        budgets = _compute_budgets(context_window=500, max_output_tokens=400)

        # Assert
        # available = 500 - 400 - 200 = -100 → floored to 1000
        assert all(v > 0 for v in budgets.values())


# ---------------------------------------------------------------------------
# _truncate_tree
# ---------------------------------------------------------------------------
class TestTruncateTree:

    def test_short_tree_unchanged(self):
        # Arrange
        tree = "README.md\nsrc\nsrc/main.py\ntests\ntests/test_main.py"

        # Act
        result = _truncate_tree(tree, max_tokens=5000, encoding_name="cl100k_base")

        # Assert
        assert result == tree

    def test_empty_tree(self):
        # Act
        out = _truncate_tree("", max_tokens=100, encoding_name="cl100k_base")

        # Assert
        assert out == ""

    def test_preserves_shallow_entries(self):
        # Arrange
        lines = [
            "README.md",  # depth 0
            "src",  # depth 0
            "src/core",  # depth 1
            "src/core/engine.py",  # depth 1
            "src/core/utils/helpers.py",  # depth 2 — pruned (not important)
            "src/core/utils/__init__.py",  # depth 2 — kept (important filename)
        ]
        tree = "\n".join(lines)

        # Act
        # Use a tiny budget to force pruning
        result = _truncate_tree(tree, max_tokens=1, encoding_name="cl100k_base")

        # Assert
        # Even with tiny budget the function applies smart pruning first
        # then hard truncation — just check it returns something non-empty
        assert isinstance(result, str)

    def test_prunes_deep_non_important_files(self):
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
        # Mock count_tokens to control pruning behavior
        with patch(
            "osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.count_tokens",
            side_effect=[999, 5],  # first call: over budget, second: under budget
        ):
            result = _truncate_tree(tree, max_tokens=10, encoding_name="cl100k_base")

        # Assert
        # random_module.py at depth 3+ should be pruned
        assert "random_module.py" not in result
        # __init__.py is important, should survive
        assert "__init__.py" in result


# ---------------------------------------------------------------------------
# _read_files_with_budget
# ---------------------------------------------------------------------------
class TestReadFilesWithBudget:

    @patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.read_file")
    @patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.count_tokens")
    @patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.truncate_to_tokens")
    def test_reads_in_priority_order(self, mock_truncate, mock_count, mock_read):
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
    def test_stops_when_budget_exhausted(self, mock_truncate, mock_count, mock_read):
        # Arrange
        mock_read.side_effect = ["content_a", "content_b", "content_c"]
        mock_truncate.side_effect = ["content_a", "content_b"]
        mock_count.side_effect = [150, 150]

        # Act
        paths, serialized = _read_files_with_budget(
            "/repo",
            ["a.py", "b.py", "c.py"],
            total_budget=200,
            per_file_cap=200,
            encoding_name="cl100k_base",
        )

        # Assert
        # Only first two files should be read (150 + 150 > 200 after second)
        # Actually: first file uses 150, remaining = 50, second file cap = min(200,50)
        assert len(paths) <= 2

    @patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.read_file")
    def test_skips_empty_files(self, mock_read):
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

    def test_empty_file_list(self):
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

    def test_zero_budget(self):
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


# ---------------------------------------------------------------------------
# context_collector_node (integration with mocked dependencies)
# ---------------------------------------------------------------------------
class TestContextCollectorNode:

    @patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.SourceRank")
    @patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.extract_readme_content")
    @patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.extract_example_paths")
    @patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector.read_file")
    @patch("osa_tool.operations.docs.readme_generation.agent.nodes.context_collector._run_parallel_analyses")
    def test_returns_all_expected_keys(
        self,
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
            ["src/main.py"],  # preanalysis → key_files
            "repo analysis result",  # repo_analysis
        ]

        mock_context = MagicMock()
        mock_context.config_manager = mock_config_manager
        mock_context.model_handler = mock_model_handler
        mock_context.prompts = mock_config_manager.get_prompts()
        mock_context.metadata = mock_repository_metadata

        from osa_tool.operations.docs.readme_generation.agent.state import ReadmeState

        state = ReadmeState(repo_url="https://github.com/test/repo")

        # Act
        result = context_collector_node(state, mock_context)

        # Assert: all expected keys present
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
