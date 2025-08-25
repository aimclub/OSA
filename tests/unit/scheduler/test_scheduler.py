from unittest.mock import MagicMock, patch

import pytest

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


def test_mode_scheduler_unsupported_mode_raises_error(mock_config_loader, mock_sourcerank, workflow_keys):
    # Arrange
    args = MagicMock()
    args.mode = "unsupported_mode"
    args.web_mode = False

    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank_instance = mock_sourcerank(repo_tree_data)

    # Assert
    with patch("osa_tool.scheduler.scheduler.load_data_metadata"):
        with pytest.raises(ValueError, match="Unsupported mode: unsupported_mode"):
            ModeScheduler(mock_config_loader, sourcerank_instance, args, workflow_keys)


def test_mode_scheduler_initialization_basic(
    mock_config_loader, mock_sourcerank, load_metadata_scheduler, mock_args_basic, workflow_keys
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank_instance = mock_sourcerank(repo_tree_data)

    with (
        patch("osa_tool.scheduler.scheduler.ModelHandlerFactory.build"),
        patch("osa_tool.scheduler.scheduler.PromptLoader"),
        patch("osa_tool.scheduler.scheduler.PlanEditor") as mock_plan_editor,
    ):

        mock_plan_editor_instance = MagicMock()
        mock_plan_editor_instance.confirm_action.return_value = {"test": "basic_plan"}
        mock_plan_editor.return_value = mock_plan_editor_instance

        # Act
        scheduler = ModeScheduler(mock_config_loader, sourcerank_instance, mock_args_basic, workflow_keys)

        # Assert
        assert scheduler.mode == "basic"
        assert "test" in scheduler.plan


def test_mode_scheduler_initialization_advanced(
    mock_config_loader, mock_sourcerank, load_metadata_scheduler, mock_args_advanced, workflow_keys
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank_instance = mock_sourcerank(repo_tree_data)

    with (
        patch("osa_tool.scheduler.scheduler.ModelHandlerFactory.build"),
        patch("osa_tool.scheduler.scheduler.PromptLoader"),
        patch("osa_tool.scheduler.scheduler.PlanEditor") as mock_plan_editor,
    ):

        mock_plan_editor_instance = MagicMock()
        mock_plan_editor_instance.confirm_action.return_value = {"test": "advanced_plan"}
        mock_plan_editor.return_value = mock_plan_editor_instance

        # Act
        scheduler = ModeScheduler(mock_config_loader, sourcerank_instance, mock_args_advanced, workflow_keys)

        # Assert
        assert scheduler.mode == "advanced"
        assert "test" in scheduler.plan


def test_mode_scheduler_initialization_auto(
    mock_config_loader, mock_sourcerank, load_metadata_scheduler, mock_args_auto, workflow_keys
):
    # Arrange
    repo_tree_data = get_mock_repo_tree("FULL")
    sourcerank_instance = mock_sourcerank(repo_tree_data)

    with (
        patch("osa_tool.scheduler.scheduler.ModelHandlerFactory.build") as mock_model_factory,
        patch("osa_tool.scheduler.scheduler.PromptLoader") as mock_prompt_loader,
        patch("osa_tool.scheduler.scheduler.extract_readme_content") as mock_extract_readme,
        patch("osa_tool.scheduler.scheduler.WorkflowManager") as mock_workflow_manager,
        patch("osa_tool.scheduler.scheduler.PlanEditor") as mock_plan_editor,
    ):
        mock_model_handler = MagicMock()
        mock_model_handler.send_request.return_value = '{"about": true, "readme": false}'
        mock_model_factory.return_value = mock_model_handler

        mock_prompt_loader_instance = MagicMock()
        mock_prompt_loader_instance.prompts = {"main_prompt": "Test prompt"}
        mock_prompt_loader.return_value = mock_prompt_loader_instance

        mock_extract_readme.return_value = "Test README"

        mock_workflow_manager_instance = MagicMock()
        mock_workflow_manager_instance.build_actual_plan.return_value = {"workflow_key": True}
        mock_workflow_manager.return_value = mock_workflow_manager_instance

        mock_plan_editor_instance = MagicMock()
        mock_plan_editor_instance.confirm_action.return_value = {"test": "auto_plan", "workflow_key": True}
        mock_plan_editor.return_value = mock_plan_editor_instance

        # Act
        scheduler = ModeScheduler(mock_config_loader, sourcerank_instance, mock_args_auto, workflow_keys)

        # Assert
        assert scheduler.mode == "auto"
        assert "test" in scheduler.plan
        assert "workflow_key" in scheduler.plan
        mock_model_handler.send_request.assert_called_once()
