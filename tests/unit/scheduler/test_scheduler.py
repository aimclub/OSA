from unittest.mock import MagicMock, patch

from osa_tool.scheduler.scheduler import ModeScheduler
from tests.utils.mocks.repo_trees import get_mock_repo_tree


def test_basic_plan_logic():
    """
    Test the basic plan returned by ModeScheduler._basic_plan.
    
    This method verifies that the helper function returns a dictionary containing the expected keys, each with a boolean value set to True. It ensures the default execution plan for the 'basic' operational mode is correctly structured and contains all predefined operations.
    
    Args:
        None.
    
    Returns:
        None.
    
    Why:
        This test validates the integrity of the default plan used by the 'basic' mode. Since the plan serves as a consistent, unconfigured starting point for core repository enhancements, confirming its structure and content guarantees that the tool's fundamental operations will be available and active as intended.
    """
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
    """
    Tests the basic initialization of ModeScheduler with minimal arguments.
    
    This test verifies that when ModeScheduler is instantiated with a basic set of arguments, it correctly generates an initial plan. The test mocks external dependencies and uses a patched PlanEditor to control the plan generation outcome.
    
    Args:
        mock_config_manager: Mocked configuration manager.
        mock_sourcerank: Factory fixture to create a mocked SourceRank instance.
        mock_repository_metadata: Mocked repository metadata.
        mock_args_basic: Mocked basic arguments for scheduler initialization.
        mock_workflow_manager: Mocked workflow manager.
    
    The test performs the following steps:
    1. Arranges a mock repository tree and a SourceRank instance using the factory fixture.
    2. Patches ModelHandlerFactory.build and PlanEditor to isolate the scheduler from external dependencies.
    3. Instantiates ModeScheduler with the provided mocked arguments.
    4. Asserts that the scheduler's generated plan matches the expected mock plan.
    
    Why this approach is used: The test isolates the scheduler's initialization logic by mocking all external components (configuration, ranking, metadata, arguments, and workflow). This ensures the test focuses solely on whether the scheduler correctly integrates these dependencies and produces a plan, without relying on actual external services or complex setups.
    """
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
        assert scheduler.plan.generated_plan == {"test": "basic_plan"}


def test_mode_scheduler_initialization_advanced(
    mock_config_manager,
    mock_sourcerank,
    mock_repository_metadata,
    mock_args_advanced,
    mock_workflow_manager,
):
    """
    Tests the initialization of ModeScheduler in advanced mode.
    
    This method verifies that when ModeScheduler is instantiated with advanced arguments,
    it correctly generates an advanced plan. The test uses mocked dependencies to isolate
    the scheduler's initialization logic and confirm the resulting plan matches expectations.
    
    Args:
        mock_config_manager: Mock configuration manager.
        mock_sourcerank: Mock SourceRank instance factory. It is called with a mock repository tree to produce a controlled SourceRank instance for the test.
        mock_repository_metadata: Mock repository metadata.
        mock_args_advanced: Mock arguments for advanced mode, which influence the scheduler's plan generation.
        mock_workflow_manager: Mock workflow manager.
    
    Returns:
        None.
    """
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
        assert scheduler.plan.generated_plan == {"test": "advanced_plan"}


def test_mode_scheduler_initialization_auto(
    mock_config_manager,
    mock_sourcerank,
    mock_repository_metadata,
    mock_args_auto,
    mock_workflow_manager,
):
    """
    Tests the automatic initialization of the ModeScheduler in test mode.
    
    This test verifies that when ModeScheduler is instantiated with automatic
    arguments (mock_args_auto), it correctly generates a plan and initializes
    its internal state. The test uses mocked dependencies to isolate the
    scheduler's initialization logic.
    
    Args:
        mock_config_manager: Mocked configuration manager.
        mock_sourcerank: Factory fixture to create SourceRank instances with
            patched methods.
        mock_repository_metadata: Mocked repository metadata.
        mock_args_auto: Mocked arguments configured for automatic mode.
        mock_workflow_manager: Mocked workflow manager.
    
    The test performs the following steps:
    1. Arranges test data and mocks external dependencies (ModelHandlerFactory,
       extract_readme_content, and PlanEditor) to control their behavior.
    2. Instantiates ModeScheduler with the provided mocked arguments and fixtures.
    3. Asserts that the scheduler's generated plan contains the expected test data
       provided by the mocked PlanEditor.
    
    The test ensures the scheduler correctly integrates its components and produces
    a valid execution plan when operating in automatic mode, without relying on
    real external services or filesystem operations.
    """
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
        assert "test" in scheduler.plan.generated_plan
        assert scheduler.plan.generated_plan["test"] == "auto_plan"
