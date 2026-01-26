from unittest.mock import MagicMock, patch

from osa_tool.scheduler.scheduler import ModeScheduler
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_basic_plan_logic():
    # Act
    plan = ModeScheduler._basic_plan()

    # Assert
    assert isinstance(plan, dict)
    assert plan["about"] is True
    assert plan["community_docs"] is True
    assert plan["organize"] is True
    assert plan["readme"] is True
    assert plan["report"] is True


def test_mode_scheduler_initialization_basic(
    mock_config_manager,
    mock_sourcerank,
    mock_repository_metadata,
    mock_args_basic,
    mock_workflow_manager,
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank_instance = mock_sourcerank(repo_tree_data)

    with (
        patch("osa_tool.scheduler.scheduler.ModelHandlerFactory.build"),
        patch("osa_tool.scheduler.scheduler.PlanEditor") as mock_plan_editor,
    ):
        mock_plan_editor_instance = MagicMock()
        mock_plan_editor_instance.confirm_action.return_value = {"test": "basic_plan"}
        mock_plan_editor.return_value = mock_plan_editor_instance

        # Act
        scheduler = ModeScheduler(
            mock_config_manager,
            sourcerank_instance,
            mock_args_basic,
            mock_workflow_manager,
            mock_repository_metadata,
        )

        # Assert
        assert scheduler.plan == {"test": "basic_plan"}


def test_mode_scheduler_initialization_advanced(
    mock_config_manager,
    mock_sourcerank,
    mock_repository_metadata,
    mock_args_advanced,
    mock_workflow_manager,
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank_instance = mock_sourcerank(repo_tree_data)

    with (
        patch("osa_tool.scheduler.scheduler.ModelHandlerFactory.build"),
        patch("osa_tool.scheduler.scheduler.PlanEditor") as mock_plan_editor,
    ):
        mock_plan_editor_instance = MagicMock()
        mock_plan_editor_instance.confirm_action.return_value = {"test": "advanced_plan"}
        mock_plan_editor.return_value = mock_plan_editor_instance

        # Act
        scheduler = ModeScheduler(
            mock_config_manager,
            sourcerank_instance,
            mock_args_advanced,
            mock_workflow_manager,
            mock_repository_metadata,
        )

        # Assert
        assert scheduler.plan == {"test": "advanced_plan"}


def test_mode_scheduler_initialization_auto(
    mock_config_manager,
    mock_sourcerank,
    mock_repository_metadata,
    mock_args_auto,
    mock_workflow_manager,
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank_instance = mock_sourcerank(repo_tree_data)

    with (
        patch("osa_tool.scheduler.scheduler.ModelHandlerFactory.build") as mock_model_factory,
        patch("osa_tool.scheduler.scheduler.extract_readme_content") as mock_extract_readme,
        patch("osa_tool.scheduler.scheduler.PlanEditor") as mock_plan_editor,
    ):
        mock_model_handler = MagicMock()
        mock_model_handler.send_request.return_value = '{"about": true, "readme": false}'
        mock_model_factory.return_value = mock_model_handler

        mock_prompt_loader_instance = MagicMock()
        mock_prompt_loader_instance.prompts = {"main_prompt": "Test prompt"}

        mock_extract_readme.return_value = "Test README"

        mock_plan_editor_instance = MagicMock()
        mock_plan_editor_instance.confirm_action.return_value = {"test": "auto_plan", "workflow_key": True}
        mock_plan_editor.return_value = mock_plan_editor_instance

        # Act
        scheduler = ModeScheduler(
            mock_config_manager,
            sourcerank_instance,
            mock_args_auto,
            mock_workflow_manager,
            mock_repository_metadata,
        )

        # Assert
        assert "test" in scheduler.plan
        assert scheduler.plan["test"] == "auto_plan"
