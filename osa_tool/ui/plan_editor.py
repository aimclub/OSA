import re
import sys
from typing import Iterable

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import (
    CompleteEvent,
    Completer,
    Completion,
    WordCompleter,
)
from prompt_toolkit.document import Document
from rich import box
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from osa_tool.arguments_parser import read_arguments_file_flat
from osa_tool.utils import build_arguments_path, logger

console = Console()


class PlanEditor:
    def __init__(self, workflow_keys: list):
        self.workflow_keys = workflow_keys
        self.info_keys = [
            "repository",
            "mode",
            "web_mode",
            "api",
            "base_url",
            "model",
            "branch",
            "output",
            "no_fork",
            "no_pull_request",
            "temperature",
            "max_tokens",
            "top_p",
        ]
        self.special_keys = ["convert_notebooks"]
        self.arguments_metadata = read_arguments_file_flat(build_arguments_path())
        self.modified_keys = set()

    def confirm_action(self, plan: dict) -> dict:
        """
        Display and optionally let the user confirm or edit the generated plan.

        Returns:
            dict: Final confirmed plan.
        """
        self._print_plan_tables(plan)

        while True:
            confirm = Prompt.ask(
                "[bold yellow]Do you want to proceed with these actions?[/bold yellow]",
                choices=["y", "n", "custom"],
                default="y",
            )
            if confirm == "y":
                return plan
            elif confirm == "n":
                logger.info("Operation canceled by user.")
                sys.exit(0)
            elif confirm == "custom":
                plan = self._manual_plan_edit(plan)
                console.print("\n[bold green]Updated plan after your edits:[/bold green]")
                self._print_plan_tables(plan)
                continue
            else:
                console.print("[red]Please enter 'y', 'n' or 'custom'.[/red]")

        return plan

    def _manual_plan_edit(self, plan: dict) -> dict:
        """
        Allow the user to manually edit plan values in interactive mode.

        Returns:
            dict: Edited plan.
        """
        console.print("\n[bold magenta]Manual plan editing mode[/bold magenta]")

        editable_keys = [k for k in plan.keys() if k not in self.info_keys]
        bool_keys = [k for k in editable_keys if isinstance(plan.get(k), bool)]

        console.print(f"\nAvailable keys for editing: [cyan]{', '.join(editable_keys)}[/cyan]\n")

        completer = WordCompleter(editable_keys, ignore_case=True)
        session = PromptSession()

        # Update plan value based on type
        while True:
            key_to_edit = (
                session.prompt(
                    "\nEnter key to edit, 'done' to finish and show current plan, 'help'/'?' for available keys, or 'multi-bool' to bulk-edit booleans: ",
                    completer=completer,
                )
                .strip()
                .lower()
            )

            if key_to_edit.lower() == "done":
                console.print("\n[bold green]Finished editing plan.[/bold green]\n")
                break

            if key_to_edit.lower() in ["help", "?"]:
                self._print_help()
                continue

            if key_to_edit == "multi-bool":
                bool_completer = MultiWordCompleter(bool_keys, ignore_case=True)
                while True:
                    keys_input = session.prompt(
                        "Enter boolean keys separated by space/comma (or 'back' to return): ",
                        completer=bool_completer,
                    ).strip()
                    if keys_input.lower() == "back":
                        break

                    # Key parsing
                    keys_list = [k.strip() for k in keys_input.replace(",", " ").split()]
                    invalid_keys = [k for k in keys_list if k not in bool_keys]

                    if invalid_keys:
                        console.print(f"[red]Invalid boolean keys: {', '.join(invalid_keys)}[/red]")
                        continue

                    new_value = Prompt.ask(
                        "Set all selected keys to (y = True / n = False / skip = no change)",
                        choices=["y", "n", "skip"],
                        default="skip",
                    )

                    if new_value == "skip":
                        continue

                    new_bool = new_value == "y"
                    for key in keys_list:
                        current_val = plan.get(key)
                        if current_val != new_bool:
                            plan[key] = new_bool
                            self._mark_key_as_changed(key, plan)
                    console.print("[green]Updated boolean keys successfully.[/green]")

                continue

            if key_to_edit not in editable_keys:
                console.print(f"[red]Key '{key_to_edit}' not found or not editable.[/red] Try again.")
                continue

            current_value = plan[key_to_edit]
            console.print(f"\n[cyan]{key_to_edit}[/cyan] (current value: [green]{current_value}[/green])")
            self._print_key_info(key_to_edit)

            if key_to_edit in self.special_keys:
                if key_to_edit == "convert_notebooks":
                    console.print(
                        "[bold]Options:[/bold]\n"
                        "[1] Enter comma-separated paths\n"
                        "[2] Clear value (None)\n"
                        "[3] Set to empty list ([])\n"
                        "[4] Keep current"
                    )
                    choice = Prompt.ask(
                        "Select an option", choices=["1", "2", "3", "4"], default="4", show_choices=True
                    )
                    if choice == "1":
                        paths_input = Prompt.ask("Enter comma-separated paths").strip()
                        new_value = [p.strip() for p in paths_input.split(",") if p.strip()]
                        plan[key_to_edit] = new_value
                    elif choice == "2":
                        plan[key_to_edit] = None
                    elif choice == "3":
                        plan[key_to_edit] = []
                    # 4 -skip

                if plan[key_to_edit] != current_value:
                    self._mark_key_as_changed(key_to_edit, plan)

                continue

            if isinstance(current_value, bool):
                new_value = Prompt.ask(
                    f"Set {key_to_edit} to (y = True / n = False / skip = no change)",
                    choices=["y", "n", "skip"],
                    default="skip",
                )
                if new_value == "y":
                    plan[key_to_edit] = True
                elif new_value == "n":
                    plan[key_to_edit] = False
                if plan[key_to_edit] != current_value:
                    self._mark_key_as_changed(key_to_edit, plan)

            elif isinstance(current_value, str) or current_value is None:
                new_value = self._prompt_and_validate_value(
                    key_to_edit,
                    f"Enter new string value for {key_to_edit} (leave blank to keep current, type 'none' to clear)",
                    value_type="str",
                    default="",
                )
                if new_value != "keep_current":
                    plan[key_to_edit] = new_value
                if plan[key_to_edit] != current_value:
                    self._mark_key_as_changed(key_to_edit, plan)

            elif isinstance(current_value, list):
                new_value = self._prompt_and_validate_value(
                    key_to_edit,
                    f"Enter comma-separated values for {key_to_edit} (leave blank to keep current, type 'none' to clear)",
                    value_type="list",
                    default="",
                )
                if new_value != "keep_current":
                    plan[key_to_edit] = new_value
                if plan[key_to_edit] != current_value:
                    self._mark_key_as_changed(key_to_edit, plan)

            else:
                console.print(f"[yellow]Unsupported type for key '{key_to_edit}'. Skipping.[/yellow]")

        return plan

    def _print_plan_tables(self, plan: dict) -> None:
        """Display the plan as structured tables in the console."""

        # Info section in console output
        console.print("\n[bold cyan]Repository and environment info:[/bold cyan]")
        info_table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE)
        info_table.add_column("Key")
        info_table.add_column("Value")

        for key in self.info_keys:
            if key in plan:
                info_table.add_row(key, str(plan[key]))
        console.print(info_table)

        # Active actions in console output
        console.print("\n[bold green]Planned actions:[/bold green]")
        actions_table = Table(show_header=True, header_style="bold green", box=box.SIMPLE)
        actions_table.add_column("Key")
        actions_table.add_column("Value")

        for key, value in plan.items():
            if key in self.info_keys or key in self.workflow_keys:
                continue

            if key in self.special_keys and value in [[]]:
                label = self._format_key_label(key)
                actions_table.add_row(label, "Search inside repository")
                continue

            if value and value not in [None, [], ""]:
                label = self._format_key_label(key)
                actions_table.add_row(label, str(value))

        self._append_workflow_section(actions_table, plan, active=True)
        console.print(actions_table)

        # Inactive actions in console output
        console.print("\n[bold red]Inactive actions:[/bold red]")
        inactive_table = Table(show_header=True, header_style="bold red", box=box.SIMPLE)
        inactive_table.add_column("Key")
        inactive_table.add_column("Value")

        for key, value in plan.items():
            if key in self.info_keys or key in self.workflow_keys:
                continue

            if key in self.special_keys and value is None:
                label = self._format_key_label(key)
                inactive_table.add_row(label, str(value))
                continue

            if not value or value == []:
                label = self._format_key_label(key)
                inactive_table.add_row(label, str(value))

        self._append_workflow_section(inactive_table, plan, active=False)
        console.print(inactive_table)

    def _append_workflow_section(self, table: Table, plan: dict, active: bool) -> None:
        """
        Append a Workflows section to a table if workflows are enabled.

        Args:
            table: Rich table object.
            plan: The current plan.
            active: Whether to append active or inactive items.
        """
        if plan.get("generate_workflows"):
            has_items = any(
                (
                    (plan.get(k) and plan.get(k) not in [None, [], ""])
                    if active
                    else (not plan.get(k) or plan.get(k) in [None, [], ""])
                )
                for k in self.workflow_keys
            )
            if not has_items:
                return

            table.add_row("", "")
            table.add_row("[bold]Workflows actions[/bold]", "")

            for key in self.workflow_keys:
                value = plan.get(key)
                if active:
                    if value and value not in [None, [], ""]:
                        label = self._format_key_label(key)
                        table.add_row(label, str(value))
                else:
                    if not value or value in [None, [], ""]:
                        label = self._format_key_label(key)
                        table.add_row(label, str(value))
        else:
            if active:
                return

            if not self.workflow_keys:
                return

            table.add_row("", "")
            table.add_row("[bold]Workflows actions[/bold]", "")

            for key in self.workflow_keys:
                value = plan.get(key)
                label = self._format_key_label(key)
                table.add_row(label, str(value))

    def _print_help(self) -> None:
        """Display help grouped by argument 'group' with descriptions, types, editability and choices."""
        groups = {"General": [], "Workflows": []}
        ordered_group_names = ["General", "Workflows"]

        for key, meta in self.arguments_metadata.items():
            if key in self.info_keys:
                continue
            elif key in self.workflow_keys:
                groups["Workflows"].append((key, meta))
            else:
                groups["General"].append((key, meta))

        console.print("\n[bold yellow]Use this help to see available keys you can edit in custom mode.[/bold yellow]\n")

        for group_name in ordered_group_names:
            items = groups.get(group_name)
            if not items:
                continue

            console.print(f"\n[bold underline blue]{group_name}[/bold underline blue]")

            help_table = Table(show_header=True, header_style="bold blue", box=box.SIMPLE)
            help_table.add_column("Key", style="cyan")
            help_table.add_column("Type", style="magenta")
            help_table.add_column("Description")
            help_table.add_column("Choices", style="green")

            for key, meta in sorted(items):
                arg_type = meta.get("type", "str")
                description = meta.get("description", "-")
                choices = ", ".join(map(str, meta.get("choices", []))) if "choices" in meta else "-"

                help_table.add_row(key, arg_type, description, choices)

            console.print(help_table)

    def _print_key_info(self, key: str) -> None:
        """Print description and example for the given key."""
        meta = self.arguments_metadata.get(key, {})
        description = meta.get("description", "No description available")
        example = meta.get("example")
        choices = meta.get("choices")
        console.print(f"[italic]Description:[/italic]\n{description}")
        if example:
            console.print(f"[italic]Example:[/italic] {example}")
        if choices:
            console.print(f"[italic]Available values:[/italic] {choices}")
        console.print()

    def _validate_input(self, key: str, value: str | list) -> bool:
        """Validate the input value for a given key against its defined choices."""
        meta = self.arguments_metadata.get(key, {})
        choices = meta.get("choices")
        arg_type = meta.get("type", "str")

        if not choices:
            return True

        if arg_type == "list":
            if not isinstance(value, list):
                return False
            return all(str(v) in map(str, choices) for v in value)
        else:
            return str(value) in map(str, choices)

    def _prompt_and_validate_value(self, key: str, prompt_text: str, value_type: str = "str", default: str = ""):
        """Prompt user for a value and validate it against choices if available."""
        while True:
            user_input = Prompt.ask(prompt_text, default=default)

            if user_input.lower() == "none":
                if value_type == "str":
                    return None
                elif value_type == "list":
                    return []
            elif user_input == "":
                return "keep_current"

            value = [item.strip() for item in user_input.split(",")] if value_type == "list" else user_input

            if self._validate_input(key, value):
                return value

            allowed = self.arguments_metadata.get(key, {}).get("choices")
            console.print(f"[red]Invalid value. Allowed values: {allowed}[/red]")

    def _mark_key_as_changed(self, key: str, plan: dict) -> None:
        """Mark a key as manually changed and update workflows flag if needed."""
        self.modified_keys.add(key)

        if key == "generate_workflows":
            if plan["generate_workflows"] is False:
                self._manual_disable_generate_workflows = True
            self._sync_generate_workflows_flag(plan)
        elif key in self._workflow_boolean_keys(plan):
            if plan.get("generate_workflows") is False and plan.get(key) is True:
                self._manual_disable_generate_workflows = False
            self._sync_generate_workflows_flag(plan)

    def _sync_generate_workflows_flag(self, plan: dict) -> None:
        """Automatically enable/disable generate_workflows based on workflow keys."""
        bool_keys = self._workflow_boolean_keys(plan, exclude={"generate_workflows"})
        any_enabled = any(plan.get(k) is True for k in bool_keys)

        if plan.get("generate_workflows"):
            if not any_enabled:
                plan["generate_workflows"] = False
                self._manual_disable_generate_workflows = False
        else:
            if any_enabled and not getattr(self, "_manual_disable_generate_workflows", False):
                plan["generate_workflows"] = True

    def _workflow_boolean_keys(self, plan: dict, exclude: set[str] = None) -> list[str]:
        """Return workflow keys with boolean values only."""
        exclude = exclude or set()
        return [k for k in self.workflow_keys if isinstance(plan.get(k), bool) and k not in exclude]

    def _format_key_label(self, key: str) -> str:
        return f"{key} *" if key in self.modified_keys else key


class MultiWordCompleter(Completer):
    def __init__(self, words, ignore_case=False):
        self.words = words
        self.ignore_case = ignore_case

    def get_completions(self, document: Document, complete_event: CompleteEvent) -> Iterable[Completion]:
        text_before_cursor = document.text_before_cursor

        parts = re.split(r"[,\s]+", text_before_cursor)
        last_word = parts[-1] if parts else ""

        for word in self.words:
            check_word = word.lower() if self.ignore_case else word
            check_last = last_word.lower() if self.ignore_case else last_word

            if check_word.startswith(check_last):
                yield Completion(word, start_position=-len(last_word))
