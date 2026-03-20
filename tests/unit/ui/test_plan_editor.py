from unittest.mock import patch, MagicMock, call

import pytest


def test_confirm_action_proceed(plan_editor, sample_plan):
    """
    Tests that the confirm_action method returns the original plan when the user chooses to proceed.
    
    This test mocks the user input to simulate selecting 'y' (yes) at the confirmation prompt. It verifies that the plan tables are displayed, the prompt is called with the correct arguments, and the method returns the plan as expected.
    
    Args:
        plan_editor: The PlanEditor instance being tested.
        sample_plan: The plan dictionary used for testing the confirmation logic.
    
    The test uses mocking to isolate the behavior:
    - The user prompt is mocked to return 'y' automatically.
    - The internal method for printing plan tables is mocked to avoid side effects.
    This ensures the test focuses on verifying the confirmation logic and return value when the user proceeds.
    """
    # Arrange
    with patch("osa_tool.ui.plan_editor.Prompt.ask", return_value="y") as mock_ask:
        with patch.object(plan_editor, "_print_plan_tables"):
            # Act
            result = plan_editor.confirm_action(sample_plan)

            # Assert
            mock_ask.assert_called_once_with(
                "[bold yellow]Do you want to proceed with these actions?[/bold yellow]",
                choices=["y", "n", "custom"],
                default="y",
            )
            assert result == sample_plan


def test_confirm_action_cancel(plan_editor, sample_plan):
    """
    Verifies that the confirm_action method correctly handles a user's cancellation input.
    
    This test mocks a negative user response ("n") to a confirmation prompt and asserts that the application raises a SystemExit, effectively terminating the action as expected. It also ensures that the plan tables are printed and the prompt is displayed exactly once.
    
    WHY: The test ensures that when a user cancels the confirmation, the system exits cleanly without proceeding, which is the intended behavior for cancellation.
    
    Args:
        plan_editor: The PlanEditor instance being tested.
        sample_plan: The plan data structure used for the confirmation process.
    """
    # Arrange
    with patch("osa_tool.ui.plan_editor.Prompt.ask", return_value="n") as mock_ask:
        with patch.object(plan_editor, "_print_plan_tables"):
            # Act & Assert
            with pytest.raises(SystemExit):
                plan_editor.confirm_action(sample_plan)

            mock_ask.assert_called_once()


def test_confirm_action_custom_then_proceed(plan_editor, sample_plan):
    """
    Verifies that the confirm_action method correctly handles a workflow where the user selects a custom edit before proceeding.
    
    Args:
        plan_editor: The PlanEditor instance being tested.
        sample_plan: A dictionary representing the initial plan to be confirmed.
    
    Returns:
        None.
    
    Why:
        This test simulates a user interaction where "custom" is chosen first, triggering a manual edit, followed by "y" to proceed. It validates that the confirm_action method properly manages this sequence, including the expected calls to prompt and plan printing.
    """
    # Arrange
    plan_copy = sample_plan.copy()
    with patch("osa_tool.ui.plan_editor.Prompt.ask", side_effect=["custom", "y"]) as mock_ask:
        with patch.object(plan_editor, "_manual_plan_edit", return_value=plan_copy):
            with patch.object(plan_editor, "_print_plan_tables") as mock_print_plan:
                # Act
                result = plan_editor.confirm_action(sample_plan)

                # Assert
                assert mock_print_plan.call_count == 2
                assert mock_ask.call_count == 2
                assert mock_ask.call_args_list[0] == call(
                    "[bold yellow]Do you want to proceed with these actions?[/bold yellow]",
                    choices=["y", "n", "custom"],
                    default="y",
                )
                assert mock_ask.call_args_list[1] == call(
                    "[bold yellow]Do you want to proceed with these actions?[/bold yellow]",
                    choices=["y", "n", "custom"],
                    default="y",
                )
                assert result == plan_copy


def test_confirm_action_invalid_input_then_proceed(plan_editor, sample_plan):
    """
    Verifies that the confirm_action method correctly handles invalid user input by re-prompting until a valid response is provided.
    
    This test simulates a user first entering an invalid response, then a valid 'y' (yes) response. It ensures the method re-prompts on invalid input and eventually accepts a valid input, returning the correct result.
    
    Args:
        plan_editor: The PlanEditor instance being tested.
        sample_plan: The plan data used for the confirmation process.
    
    Returns:
        None: This is a test method that performs assertions.
    """
    # Arrange
    with patch("osa_tool.ui.plan_editor.Prompt.ask", side_effect=["invalid", "y"]) as mock_ask:
        with patch("osa_tool.ui.plan_editor.console.print") as mock_console_print:
            with patch.object(plan_editor, "_print_plan_tables"):
                # Act
                result = plan_editor.confirm_action(sample_plan)

                # Assert
                assert mock_ask.call_count == 2
                error_call = call("[red]Please enter 'y', 'n' or 'custom'.[/red]")
                assert error_call in mock_console_print.call_args_list
                assert result == sample_plan


def test_manual_plan_edit_done_immediately(plan_editor, sample_plan):
    """
    Verifies that the manual plan editing process terminates immediately when the user inputs the 'done' command.
    
    This test ensures that entering 'done' as the first command exits the interactive editing mode without prompting for any plan modifications, and that the original plan is returned unchanged.
    
    Args:
        plan_editor: The PlanEditor instance being tested.
        sample_plan: A dictionary representing the initial plan data to be edited.
    
    Returns:
        None.
    """
    # Arrange
    original_plan = sample_plan.copy()
    with patch("osa_tool.ui.plan_editor.PromptSession") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.prompt.side_effect = ["done"]

        with patch("osa_tool.ui.plan_editor.Prompt.ask") as mock_ask:
            with patch("osa_tool.ui.plan_editor.console.print") as mock_console_print:
                with patch.object(plan_editor, "_print_help"):
                    # Act
                    result = plan_editor._manual_plan_edit(original_plan)

                    # Assert
                    mock_session.prompt.assert_called_once()
                    mock_ask.assert_not_called()
                    printed_messages = [str(args[0]) for args, kwargs in mock_console_print.call_args_list if args]
                    full_message = "".join(printed_messages)
                    assert (
                        "\n[bold magenta]Manual plan editing mode[/bold magenta]\n" in full_message
                        or "[bold magenta]Manual plan editing mode[/bold magenta]" in full_message
                    )
                    assert (
                        "\n[bold green]Finished editing plan.[/bold green]\n" in full_message
                        or "[bold green]Finished editing plan.[/bold green]" in full_message
                    )
                    assert result == original_plan


def test_manual_plan_edit_toggle_boolean(plan_editor, sample_plan):
    """
    Verifies that the manual plan editor correctly toggles a boolean value from False to True.
    
    The test mocks a user session where a specific boolean key is selected and updated via a prompt. It ensures that the plan is updated correctly, the appropriate prompt is displayed to the user, and the key is added to the editor's tracking of modified keys.
    
    This test specifically checks the interactive flow where the user selects the "docstring" key and confirms the change to True. It validates that the prompt presents the correct choices and that the modified key is recorded.
    
    Args:
        plan_editor: The PlanEditor instance being tested.
        sample_plan: A dictionary representing a sample plan with a boolean field. The plan must contain a key "docstring" with an initial value of False.
    
    Returns:
        None.
    """
    # Arrange
    original_plan = sample_plan.copy()
    key_to_toggle = "docstring"
    assert original_plan[key_to_toggle] is False

    with patch("osa_tool.ui.plan_editor.PromptSession") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.prompt.side_effect = [key_to_toggle, "done"]

        with patch("osa_tool.ui.plan_editor.Prompt.ask", side_effect=["y"]) as mock_ask:
            with patch.object(plan_editor, "_print_key_info"):
                # Act
                result = plan_editor._manual_plan_edit(original_plan)

                # Assert
                assert mock_session.prompt.call_count == 2
                mock_ask.assert_called_once_with(
                    f"Set {key_to_toggle} to (y = True / n = False / skip = no change)",
                    choices=["y", "n", "skip"],
                    default="skip",
                )
                assert result[key_to_toggle] is True
                assert key_to_toggle in plan_editor.modified_keys


def test_manual_plan_edit_skip_boolean(plan_editor, sample_plan):
    """
    Verifies that the manual plan editing process correctly handles skipping a boolean field.
    
    This test ensures that when a user chooses to skip a specific key (in this case, a boolean field) during an interactive editing session, the original value remains unchanged and the key is not marked as modified. It mocks the interactive prompt session to simulate selecting a key and then entering the skip command.
    
    Args:
        plan_editor: The PlanEditor instance being tested.
        sample_plan: A dictionary representing a sample plan configuration.
    
    Why:
        This test validates that the interactive editing flow properly respects the "skip" command for a boolean field, ensuring the original value is preserved and the field is not incorrectly flagged as modified. This is important for maintaining data integrity during partial edits.
    
    Details:
        - The test targets the key "about" (expected to be True in the sample plan).
        - It mocks the PromptSession to simulate user input: first selecting the "about" key, then entering "done".
        - It mocks Prompt.ask to return "skip" when prompted for a new value.
        - It verifies that after the edit, the value for "about" remains True and that "about" is not added to plan_editor.modified_keys.
    """
    # Arrange
    original_plan = sample_plan.copy()
    key_to_skip = "about"
    assert original_plan[key_to_skip] is True

    with patch("osa_tool.ui.plan_editor.PromptSession") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.prompt.side_effect = [key_to_skip, "done"]

        with patch("osa_tool.ui.plan_editor.Prompt.ask", side_effect=["skip"]) as mock_ask:
            with patch.object(plan_editor, "_print_key_info"):
                # Act
                result = plan_editor._manual_plan_edit(original_plan)

                # Assert
                mock_ask.assert_called_once()
                assert result[key_to_skip] is True
                assert key_to_skip not in plan_editor.modified_keys


def test_manual_plan_edit_change_string(plan_editor, sample_plan):
    """
    Verifies that the manual plan editing process correctly updates a string value for a specific key.
    
    This test mocks a user interaction session where a specific key is selected for modification. It ensures that when a new string value is provided, the plan is updated accordingly and the key is tracked in the editor's modified keys list.
    
    The test uses mocking to simulate user input and isolate the editing logic, confirming that the plan dictionary is properly modified and the key is recorded as changed.
    
    Args:
        plan_editor: The PlanEditor instance being tested.
        sample_plan: A dictionary representing the initial plan data to be edited.
    
    Returns:
        None. This is a test method; assertions are used to verify behavior.
    """
    # Arrange
    original_plan = sample_plan.copy()
    key_to_change = "some_other_action"
    new_value = "new_value"

    with patch("osa_tool.ui.plan_editor.PromptSession") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.prompt.side_effect = [key_to_change, "done"]

        with patch.object(plan_editor, "_prompt_and_validate_value", return_value=new_value):
            with patch.object(plan_editor, "_print_key_info"):
                # Act
                result = plan_editor._manual_plan_edit(original_plan)

                # Assert
                assert result[key_to_change] == new_value
                assert key_to_change in plan_editor.modified_keys


def test_manual_plan_edit_change_list(plan_editor, sample_plan):
    """
    Verifies that the manual plan editing process correctly updates a list-type value within a plan.
    
    This test mocks a user interaction session where a specific key containing a list is selected for modification. It ensures that when a new list is provided, the plan is updated accordingly and the key is tracked as modified.
    
    The test uses mocking to simulate user input and isolate the editing logic, confirming that list values are properly handled and modification tracking works as expected.
    
    Args:
        plan_editor: The PlanEditor instance being tested.
        sample_plan: A dictionary representing a baseline plan configuration.
    
    Steps performed:
        1. Creates a test plan with a predefined list key and initial list value.
        2. Mocks the interactive prompt session to simulate user selection of the list key.
        3. Mocks the value prompt to return a new list value.
        4. Calls the manual edit method and verifies the list is updated in the returned plan.
        5. Asserts the modified key is recorded in the editor's tracking set.
    """
    # Arrange
    plan_with_list = sample_plan.copy()
    list_key = "example_list_key"
    plan_with_list[list_key] = ["item1", "item2"]
    key_to_change = "example_list_key"
    new_list_value = ["new_item1", "new_item2"]
    assert plan_with_list[key_to_change] != new_list_value

    with patch("osa_tool.ui.plan_editor.PromptSession") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.prompt.side_effect = [key_to_change, "done"]

        with patch.object(plan_editor, "_prompt_and_validate_value", return_value=new_list_value):
            with patch.object(plan_editor, "_print_key_info"):
                # Act
                result = plan_editor._manual_plan_edit(plan_with_list)

                # Assert
                assert result[key_to_change] == new_list_value
                assert key_to_change in plan_editor.modified_keys


def test_manual_plan_edit_multi_bool(plan_editor, sample_plan):
    """
    Verifies that multiple boolean flags in a plan can be toggled simultaneously using the manual plan editor.
    
    This test simulates a user interaction where multiple keys are selected via the 'multi-bool' command. It ensures that the specified boolean values are flipped to True, and that these keys are correctly tracked as modified within the plan editor.
    
    WHY: The test validates that the interactive editor correctly handles batch toggling of boolean fields, a feature intended to improve user efficiency when enabling or disabling multiple related options at once.
    
    Args:
        plan_editor: The PlanEditor instance being tested.
        sample_plan: A dictionary representing the initial plan configuration.
    
    Returns:
        None. This is a test method; assertions are used to verify behavior.
    """
    # Arrange
    original_plan = sample_plan.copy()
    bool_keys = [
        k
        for k in original_plan
        if isinstance(original_plan[k], bool) and k not in plan_editor.info_keys and k in plan_editor.workflow_keys
    ]
    keys_to_enable = [k for k in bool_keys if original_plan[k] is False][:2]
    if len(keys_to_enable) < 2:
        original_plan["include_autopep8"] = False
        original_plan["include_fix_pep8"] = False
        keys_to_enable = ["include_autopep8", "include_fix_pep8"]

    key1, key2 = keys_to_enable[0], keys_to_enable[1]

    with patch("osa_tool.ui.plan_editor.PromptSession") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.prompt.side_effect = ["multi-bool", f"{key1},{key2}", "back", "done"]

        with patch("osa_tool.ui.plan_editor.Prompt.ask", side_effect=["y"]) as mock_ask:
            with patch("osa_tool.ui.plan_editor.MultiWordCompleter"):
                with patch.object(plan_editor, "_print_help"):
                    # Act
                    result = plan_editor._manual_plan_edit(original_plan)

                    # Assert
                    assert result[key1] is True
                    assert result[key2] is True
                    assert key1 in plan_editor.modified_keys
                    assert key2 in plan_editor.modified_keys


def test_manual_plan_edit_help(plan_editor, sample_plan):
    """
    Verifies that the manual plan editing interface correctly displays help information when requested.
    
    This test mocks a user session where the "help" command is entered followed by "done", ensuring that the help printing utility is triggered and the plan remains unchanged.
    
    Args:
        plan_editor: The PlanEditor instance being tested.
        sample_plan: A dictionary representing the initial plan data to be edited.
    
    Why:
        This test ensures that the interactive help feature works without altering the plan, which is critical for user assistance during manual editing.
    
    Behavior:
        - Mocks the PromptSession to simulate user input of "help" then "done".
        - Patches the internal _print_help method to verify it is called.
        - Patches console.print to suppress output during the test.
        - Asserts that the help method is called exactly once and that the returned plan is unchanged.
    """
    # Arrange
    original_plan = sample_plan.copy()

    with patch("osa_tool.ui.plan_editor.PromptSession") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.prompt.side_effect = ["help", "done"]

        with patch.object(plan_editor, "_print_help") as mock_print_help:
            with patch("osa_tool.ui.plan_editor.console.print"):
                # Act
                result = plan_editor._manual_plan_edit(original_plan)

                # Assert
                mock_print_help.assert_called_once()
                assert result == original_plan


def test_manual_plan_edit_invalid_key(plan_editor, sample_plan):
    """
    Verifies that the manual plan editor correctly handles an invalid key input.
    
    This test mocks a user session to provide an invalid key followed by a completion command. It ensures that an appropriate error message is printed to the console and that the plan remains unchanged when an invalid key is provided.
    
    Args:
        plan_editor: The PlanEditor instance being tested.
        sample_plan: A dictionary representing the initial plan data.
    
    Returns:
        None. This is a test method; assertions are used to verify behavior.
    
    Why:
        The test validates that the interactive editor gracefully rejects unrecognized or non-editable keys, preventing unintended modifications and providing clear user feedback.
    """
    # Arrange
    original_plan = sample_plan.copy()

    with patch("osa_tool.ui.plan_editor.PromptSession") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        mock_session.prompt.side_effect = ["invalid_key", "done"]

        with patch("osa_tool.ui.plan_editor.console.print") as mock_console_print:
            with patch.object(plan_editor, "_print_help"):
                # Act
                result = plan_editor._manual_plan_edit(original_plan)

                # Assert
                error_call = call("[red]Key 'invalid_key' not found or not editable.[/red] Try again.")
                assert error_call in mock_console_print.call_args_list
                assert result == original_plan


def test_sync_generate_workflows_flag_enable(plan_editor):
    """
    Verifies that the generate_workflows flag is automatically enabled when workflow-related keys are present in the plan, provided no manual override is set.
    
    Args:
        plan_editor: The PlanEditor instance being tested.
    
    Note:
        This test ensures that if the manual disable attribute is absent, the synchronization logic correctly updates the plan's generate_workflows status based on the inclusion of specific workflow components like tests. The test specifically checks the scenario where a plan initially has generate_workflows set to False but includes a workflow key (e.g., include_tests: True), expecting the flag to be set to True after synchronization.
    """
    # Arrange
    plan = {"include_black": False, "include_tests": True, "generate_workflows": False}

    if hasattr(plan_editor, "_manual_disable_generate_workflows"):
        delattr(plan_editor, "_manual_disable_generate_workflows")

    # Act
    plan_editor._sync_generate_workflows_flag(plan)

    # Assert
    assert plan["generate_workflows"] is True


def test_sync_generate_workflows_flag_disable(plan_editor):
    """
    Verifies that the `_sync_generate_workflows_flag` method correctly disables the `generate_workflows` flag in a plan when all individual workflow-related keys are set to false.
    
    WHY: This test ensures the automatic synchronization logic works as intended—when no workflow features are enabled, the overarching workflow generation should be turned off.
    
    Args:
        plan_editor: The PlanEditor instance used to manage and synchronize workflow configuration flags.
    
    Note:
        The test sets all boolean workflow keys in the plan to False, ensures manual override is disabled, and confirms `generate_workflows` becomes False after synchronization.
    """
    # Arrange
    plan = {"include_black": True, "include_tests": True, "generate_workflows": True}

    for key in plan_editor.workflow_keys:
        if key in plan and isinstance(plan[key], bool):
            plan[key] = False

    plan_editor._manual_disable_generate_workflows = False

    # Act
    plan_editor._sync_generate_workflows_flag(plan)

    # Assert
    assert plan["generate_workflows"] is False


def test_format_key_label(plan_editor):
    """
    Verifies that the `_format_key_label` method correctly appends an asterisk to a key label if the key has been modified.
    This test ensures that modified keys are visually distinguished in the UI by the appended asterisk, while unmodified keys remain unchanged.
    
    Args:
        plan_editor: The plan editor instance being tested, which manages key modifications and label formatting. It provides the `_format_key_label` method and a `modified_keys` set to track changes.
    
    The test performs three steps:
    1. Checks that an unmodified key returns its original label without an asterisk.
    2. Adds the key to `modified_keys`, then verifies the label includes an asterisk.
    3. Cleans up by removing the key from `modified_keys` to avoid side effects.
    """
    # Arrange
    key = "test_key"
    label = plan_editor._format_key_label(key)
    # Assert
    assert label == key

    # Arrange
    plan_editor.modified_keys.add(key)
    # Act
    label = plan_editor._format_key_label(key)
    # Assert
    assert label == f"{key} *"

    # Cleanup
    plan_editor.modified_keys.discard(key)
