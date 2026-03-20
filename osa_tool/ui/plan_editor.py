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

from osa_tool.utils.arguments_parser import read_arguments_file_flat
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import build_arguments_path

console = Console()


class PlanEditor:
    """
    PlanEditor is an interactive command-line tool for editing and validating configuration plans.
    
        This class provides an interface for users to view, modify, and confirm configuration plans
        through structured console tables. It supports workflow management, input validation against
        predefined choices, and tracks modifications to configuration keys.
    
        Attributes:
            workflow_keys (list): A list of keys representing workflows.
            info_keys (list): A list of predefined configuration and metadata keys.
            special_keys (list): A list of keys designated as special processing keys.
            arguments_metadata (dict): A flattened dictionary of arguments read from the arguments YAML file.
            modified_keys (set): A set to track keys that have been modified.
    
        Methods:
            __init__: Initializes the PlanEditor with workflow keys and loads configuration metadata.
            confirm_action: Displays the plan and allows user confirmation or editing.
            _manual_plan_edit: Enables interactive manual editing of plan values.
            _print_plan_tables: Renders the plan as formatted console tables.
            _append_workflow_section: Adds workflow sections to display tables.
            _print_help: Shows help information grouped by argument categories.
            _print_key_info: Displays detailed information about a specific key.
            _validate_input: Validates user input against allowed choices for a key.
            _prompt_and_validate_value: Prompts for and validates user input.
            _mark_key_as_changed: Tracks manually modified keys and updates workflow flags.
            _sync_generate_workflows_flag: Automatically manages the generate_workflows flag.
            _workflow_boolean_keys: Identifies workflow keys with boolean values.
            _format_key_label: Formats key labels with modification indicators.
    """

    def __init__(self, workflow_keys: list):
        """
        Initializes a new instance of the PlanEditor.
        
        Args:
            workflow_keys: A list of keys representing workflows that the editor will manage.
        
        Initializes the following class fields:
            workflow_keys (list): A list of keys representing workflows.
            info_keys (list): A list of predefined configuration and metadata keys used for project settings and model parameters.
            special_keys (list): A list of keys designated as special processing keys, such as "convert_notebooks".
            arguments_metadata (dict): A flattened dictionary of all configuration arguments read from the arguments YAML file. This provides centralized access to CLI argument definitions.
            modified_keys (set): A set to track keys that have been modified during editing operations, useful for change detection.
        
        WHY: The constructor sets up the editor's internal state by loading persistent configuration from a YAML file and defining categories of keys (workflow, info, special) to organize and manage different types of repository operations effectively.
        """
        self.workflow_keys = workflow_keys
        self.info_keys = [
            "use_single_model",
            "config_file",
            "repository",
            "mode",
            "web_mode",
            "api",
            "base_url",
            "model",
            "model_docstring",
            "model_readme",
            "model_validation",
            "model_general",
            "branch",
            "output",
            "no_fork",
            "no_pull_request",
            "temperature",
            "max_tokens",
            "context_window",
            "top_p",
            "max_retries",
        ]
        self.special_keys = ["convert_notebooks"]
        self.arguments_metadata = read_arguments_file_flat(build_arguments_path())
        self.modified_keys = set()

    def confirm_action(self, plan: dict) -> dict:
        """
        Display and optionally let the user confirm or edit the generated workflow plan.
        
        The method presents the plan in a structured table format and enters an interactive loop.
        The user can choose to proceed with the plan as-is, cancel the operation entirely, or enter a custom editing mode to modify the plan manually.
        This interactive confirmation ensures the user reviews and approves the automated plan before any actions are executed, preventing unintended changes.
        
        Args:
            plan: The generated workflow plan dictionary to be reviewed.
        
        Returns:
            dict: The final confirmed plan, either unchanged or as edited by the user.
        
        Why:
            This step is critical for user control and safety. It allows verification of the automatically generated plan and provides an opportunity to adjust settings before the tool performs any repository modifications, ensuring the actions align with user intent.
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
        
        The method enters a loop where the user can repeatedly select keys to modify.
        It supports editing individual keys, bulk‑editing boolean keys, and provides
        special handling for certain keys (like 'convert_notebooks'). After each change,
        the method marks the key as manually changed to track user overrides.
        
        Args:
            plan: The workflow plan dictionary to be edited. The method modifies this
                  dictionary in‑place and returns the updated version.
        
        Returns:
            dict: The edited plan dictionary with user modifications applied.
        
        Why:
            This interactive mode gives users fine‑grained control over the workflow
            configuration. It is used when automatic plan generation does not produce
            the desired settings, or when the user wants to adjust specific values
            before execution. The method ensures that only editable keys (excluding
            informational keys) can be changed, and it validates inputs according to
            each key’s expected type and allowed choices.
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
        """
        Display the plan as structured tables in the console.
        
        The plan is divided into three distinct sections for clarity:
        1. Repository and environment info: Displays keys from `self.info_keys` that are present in the plan.
        2. Planned actions: Shows active (non-empty) items, excluding info and workflow keys. Special keys with empty list values are labeled as "Search inside repository".
        3. Inactive actions: Shows inactive (empty or falsy) items, excluding info and workflow keys. Special keys with `None` values are included here.
        
        WHY: This structured presentation helps users quickly distinguish between informational metadata, intended actions to be performed, and actions that are currently disabled or pending.
        
        Args:
            plan: The plan dictionary containing keys and values to be displayed.
        
        Returns:
            None
        """

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
        
        This method conditionally adds a "Workflows actions" section to a Rich table, displaying workflow-related keys and their values from the plan. The behavior differs based on whether workflows are enabled in the plan and whether active or inactive items are requested.
        
        If workflows are enabled (`generate_workflows` is True), it appends rows for keys where the value is considered "active" (non-empty and truthy) or "inactive" (empty, None, or falsy), depending on the `active` parameter. If no items match the criteria, the section is skipped.
        
        If workflows are not enabled, the method only appends a section when `active` is False, showing all workflow keys regardless of their values. This allows displaying inactive or placeholder workflow configurations even when workflows are disabled.
        
        Args:
            table: Rich table object to which rows will be added.
            plan: The current plan dictionary containing workflow keys and values.
            active: If True, append active (non-empty) items; if False, append inactive (empty) items.
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
        """
        Display help for editable arguments in custom mode, grouped by category with detailed metadata.
        
        This method generates a formatted help table showing available configuration keys that users can modify
        when the editor is in custom mode. Arguments are organized into predefined groups ("General" and "Workflows")
        to improve readability and logical separation. For each argument, the table displays the key name, data type,
        description, and available choices (if any).
        
        Args:
            None (uses instance attributes).
        
        Why:
            The help display is intended to guide users in custom mode by clearly presenting which arguments are editable,
            their constraints, and how they are categorized. This prevents confusion and helps users make informed edits
            without needing to inspect the underlying metadata structure directly.
        
        Behavior:
            - Skips keys marked as informational (self.info_keys) since they are not editable.
            - Separates workflow-related keys (self.workflow_keys) into a dedicated "Workflows" group.
            - All other editable keys are placed in the "General" group.
            - Outputs a color‑formatted table for each group using the Rich console library.
            - Sorts keys alphabetically within each group for consistent presentation.
        """
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
        """
        Print description and example for the given key.
        
        Retrieves metadata for the specified key from the internal arguments_metadata dictionary
        and prints a formatted display to the console. This is used to provide contextual help
        to users about available command arguments or configuration options.
        
        Args:
            key: The key for which to retrieve and display metadata.
        
        The output includes:
            - A description of the key.
            - An example value, if available.
            - Available choices (predefined valid values), if provided.
        
        If metadata for the key is not found, default placeholder text is shown.
        """
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
        """
        Validate the input value for a given key against its defined choices.
        
        This method checks whether a provided value is permissible for a specific argument,
        based on the choices defined in the argument's metadata. It supports both single
        string values and lists of values, ensuring type‑appropriate validation.
        
        Args:
            key: The argument name whose metadata is used to retrieve validation rules.
            value: The value to validate; can be a string or a list of strings.
        
        Returns:
            True if the value is valid according to the choices; False otherwise.
        
        Why:
            The method ensures that user‑supplied inputs conform to the allowed options
            defined for each argument, preventing invalid data from being processed in
            subsequent steps. This is essential for maintaining data integrity and
            avoiding runtime errors when the argument choices are restricted.
        """
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
        """
        Prompt user for a value and validate it against choices if available.
        
        This method repeatedly asks the user for input until a valid value is provided.
        It handles special inputs like "none" (returning None or an empty list) and an empty string
        (returning "keep_current" to indicate no change). For list-type inputs, it splits comma-separated
        values and strips whitespace. The input is validated against the allowed choices defined for the
        given key in the arguments metadata.
        
        Args:
            key: The argument name whose metadata defines the allowed choices for validation.
            prompt_text: The text displayed to the user when prompting for input.
            value_type: The expected type of the input; either "str" for a single string or "list" for a comma-separated list.
            default: The default value presented to the user if no input is provided.
        
        Returns:
            The validated user input, which may be a string, a list of strings, None, an empty list, or the special string "keep_current".
            Returns "keep_current" when the user enters an empty string, signaling that the existing value should be retained.
            Returns None for "str" type or an empty list for "list" type when the user inputs "none".
        
        Why:
            This method ensures interactive, type‑aware collection of user inputs with immediate validation,
            preventing invalid data from proceeding further in the editing workflow. It supports flexible
            input handling for both single and multiple values while respecting the predefined constraints
            for each argument.
        """
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
        """
        Mark a key as manually changed and update workflows flag if needed.
        
        This method records that a specific configuration key has been modified by the user.
        If the changed key is related to workflow generation, it also manages a manual override
        flag and synchronizes the overall 'generate_workflows' setting accordingly.
        
        Args:
            key: The configuration key that was manually changed.
            plan: The workflow plan dictionary being edited. The method may modify this
                  dictionary in-place via helper calls.
        
        Why:
            - Tracking modified keys allows the editor to know which settings have been
              altered by user input.
            - Special handling for 'generate_workflows' and other workflow boolean keys
              ensures that manual user decisions are respected. For example, if a user
              explicitly disables 'generate_workflows', that choice is preserved until
              they manually re-enable it or change another workflow key in a way that
              clears the manual override.
            - The synchronization maintains consistency: workflows are generated only
              when at least one workflow type is enabled, and not generated when all
              are disabled, unless the user has manually overridden this logic.
        """
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
        """
        Automatically enable or disable the 'generate_workflows' flag in a plan based on the state of other workflow boolean keys.
        
        This method ensures that 'generate_workflows' is only active when at least one other workflow boolean key is enabled, and only inactive when all other such keys are disabled. It respects a manual override: if a user has manually disabled 'generate_workflows', it will not be automatically re-enabled until the manual flag is cleared.
        
        Args:
            plan: The workflow plan dictionary to update. The method modifies the 'generate_workflows' key in-place.
        
        Why:
            The flag synchronization prevents the system from generating workflows when no specific workflow types are requested, and conversely, ensures workflows are generated when at least one type is active. The manual disable flag preserves user intent, preventing automatic re-enablement after a deliberate user action.
        """
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
        """
        Return workflow keys with boolean values only, filtering out any keys that are explicitly excluded.
        
        This method scans the predefined workflow keys of the PlanEditor instance and identifies which of those keys,
        when looked up in the provided plan dictionary, have boolean values. It is used to isolate configuration flags
        or toggle settings within a workflow plan, which is helpful for validation, serialization, or UI rendering
        where boolean options need special handling.
        
        Args:
            plan: The workflow plan dictionary to inspect for boolean values at the workflow keys.
            exclude: A set of keys to omit from the returned list, even if they have boolean values.
                     If not provided, defaults to an empty set.
        
        Returns:
            A list of workflow keys that correspond to boolean values in the plan and are not in the excluded set.
        """
        exclude = exclude or set()
        return [k for k in self.workflow_keys if isinstance(plan.get(k), bool) and k not in exclude]

    def _format_key_label(self, key: str) -> str:
        """
        Formats a key label by appending an indicator if the key has been modified.
        This is used to visually distinguish keys that have unsaved changes in the editor.
        
        Args:
            key: The name of the key to be formatted.
        
        Returns:
            str: The formatted key label. If the key is present in the instance's `modified_keys` set, an asterisk (" *") is appended to the key name; otherwise, the original key string is returned unchanged.
        """
        return f"{key} *" if key in self.modified_keys else key


class MultiWordCompleter(Completer):
    """
    MultiWordCompleter is a class designed to provide word completion suggestions based on a predefined list of words. It supports configurable case sensitivity for matching.
    
        Attributes:
            words: Stores the provided list of words.
            ignore_case: Stores the preference for case-insensitive operations.
    
        Methods:
            __init__: Initializes the instance with a list of words and case sensitivity settings.
            get_completions: Provides completion suggestions based on the text before the cursor.
    """

    def __init__(self, words, ignore_case=False):
        """
        Initialize the instance with a list of words and case sensitivity settings.
        
        Args:
            words: The collection of words to be stored or processed. These words are used for autocompletion operations.
            ignore_case: A boolean flag indicating whether string comparisons should ignore character casing. When True, matching is case-insensitive.
        
        Attributes:
            words: Stores the provided list of words.
            ignore_case: Stores the preference for case-insensitive operations. This setting influences how completions are matched against input.
        """
        self.words = words
        self.ignore_case = ignore_case

    def get_completions(self, document: Document, complete_event: CompleteEvent) -> Iterable[Completion]:
        """
        Provides completion suggestions based on the text before the cursor.
        
        This method parses the document's text to identify the last word being typed and compares it against a predefined list of words. It yields completion candidates that match the prefix, accounting for case sensitivity settings.
        
        Args:
            document: The document object containing the current text and cursor position.
            complete_event: The event that triggered the completion request.
        
        Yields:
            Iterable[Completion]: An iterable of Completion objects representing the suggested words and their relative start positions.
        
        Notes:
            The method splits the text before the cursor using a regular expression that matches commas or whitespace (`[,\s]+`) to isolate the last word fragment. This allows completions to be suggested even when the user is typing within a larger, delimited text segment. Each candidate from the internal word list is compared with the last word fragment, respecting the completer's case‑sensitivity setting (`ignore_case`). When a match is found, the completion is yielded with a `start_position` set to the negative length of the last word, ensuring the suggestion replaces exactly that fragment.
        """
        text_before_cursor = document.text_before_cursor

        parts = re.split(r"[,\s]+", text_before_cursor)
        last_word = parts[-1] if parts else ""

        for word in self.words:
            check_word = word.lower() if self.ignore_case else word
            check_last = last_word.lower() if self.ignore_case else last_word

            if check_word.startswith(check_last):
                yield Completion(word, start_position=-len(last_word))
