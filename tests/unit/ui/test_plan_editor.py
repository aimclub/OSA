from unittest.mock import patch, MagicMock, call

import pytest


def test_confirm_action_proceed(plan_editor, sample_plan):
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
    # Arrange
    with patch("osa_tool.ui.plan_editor.Prompt.ask", return_value="n") as mock_ask:
        with patch.object(plan_editor, "_print_plan_tables"):
            # Act & Assert
            with pytest.raises(SystemExit):
                plan_editor.confirm_action(sample_plan)

            mock_ask.assert_called_once()


def test_confirm_action_custom_then_proceed(plan_editor, sample_plan):
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
    # Arrange
    plan = {"include_black": False, "include_tests": True, "generate_workflows": False}

    if hasattr(plan_editor, "_manual_disable_generate_workflows"):
        delattr(plan_editor, "_manual_disable_generate_workflows")

    # Act
    plan_editor._sync_generate_workflows_flag(plan)

    # Assert
    assert plan["generate_workflows"] is True


def test_sync_generate_workflows_flag_disable(plan_editor):
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
