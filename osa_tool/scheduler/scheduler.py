import json
import os
import sys

from pydantic import ValidationError

from osa_tool.analytics.metadata import load_data_metadata
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.config.settings import ConfigLoader
from osa_tool.models.models import ModelHandlerFactory, ModelHandler
from osa_tool.readmegen.postprocessor.response_cleaner import process_text
from osa_tool.scheduler.prompts import PromptLoader, PromptConfig
from osa_tool.utils import logger, parse_folder_name, extract_readme_content

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import WordCompleter
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table
from rich import box

console = Console()

class ModeScheduler:
    def __init__(self,
                 config: ConfigLoader,
                 sourcerank: SourceRank,
                 args,
                 workflow_keys: list):
        self.mode = args.mode
        self.args = args
        self.workflow_keys = workflow_keys
        self.config = config.config
        self.sourcerank = sourcerank
        self.model_handler: ModelHandler = ModelHandlerFactory.build(self.config)
        self.repo_url = self.config.git.repository
        self.metadata = load_data_metadata(self.repo_url)
        self.base_path = os.path.join(
            os.getcwd(),
            parse_folder_name(self.repo_url)
        )
        self.prompts = PromptLoader().prompts
        self.info_keys = [
            "repository",
            "mode",
            "api",
            "base_url",
            "model",
            "branch",
            "not_publish_results"
        ]

        self.plan = self._select_plan()

    @staticmethod
    def _basic_plan() -> dict:
        plan = {
            "report": True,
            "community_docs": True,
            "readme": True,
            "organize": True,
            "about": True,
        }
        return plan

    def _select_plan(self) -> dict:
        plan = dict(vars(self.args))
        if self.mode == "basic":
            logger.info("Basic mode selected for task scheduler.")

            for key, value in self._basic_plan().items():
                plan[key] = value

        elif self.mode == "advanced":
            logger.info("Advanced mode selected for task scheduler.")

        elif self.mode == "auto":
            logger.info("Auto mode selected for task scheduler.")
            auto_plan = self._make_request_for_auto_mode()

            for key, value in auto_plan.items():
                plan[key] = value
        else:
            raise ValueError(f"Unsupported mode: {self.mode}")

        return self._confirm_action(plan)

    def _make_request_for_auto_mode(self) -> dict:
        main_prompt = self.prompts.get("main_prompt")
        formatted_prompt = main_prompt.format(
            license_presence=self.sourcerank.license_presence(),
            about_section=self.metadata.description,
            repository_tree=self.sourcerank.tree,
            readme_content=extract_readme_content(self.base_path),
        )

        response = self.model_handler.send_request(formatted_prompt)
        cleaned_response = process_text(response)

        try:
            parsed_json = json.loads(cleaned_response)
            validated_data = PromptConfig.model_validate(parsed_json)
            return validated_data.model_dump()
        except (ValidationError, json.JSONDecodeError) as e:
            raise ValueError(f"JSON parsing error: {e}")

    def _confirm_action(self, plan: dict) -> dict:
        self._print_plan_tables(plan)

        while True:
            confirm = Prompt.ask(
                "[bold yellow]Do you want to proceed with these actions?[/bold yellow]",
                choices=["y", "n", "custom"],
                default="y"
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
        console.print("\n[bold magenta]Manual plan editing mode[/bold magenta]")

        editable_keys = [k for k in plan.keys() if k not in self.info_keys]

        console.print(f"\nAvailable keys for editing: [cyan]{', '.join(editable_keys)}[/cyan]")
        console.print("Type [bold]done[/bold] to finish editing.")

        completer = WordCompleter(editable_keys, ignore_case=True)
        session = PromptSession()

        while True:
            key_to_edit = session.prompt("\nEnter the key you want to edit (or 'done' to finish): ", completer=completer).strip()

            if key_to_edit.lower() == "done":
                console.print("\n[bold green]Finished editing plan.[/bold green]\n")
                break

            if key_to_edit not in editable_keys:
                console.print(f"[red]Key '{key_to_edit}' not found or not editable.[/red] Try again.")
                continue

            current_value = plan[key_to_edit]
            console.print(f"[cyan]{key_to_edit}[/cyan] (current value: [green]{current_value}[/green])")

            if isinstance(current_value, bool):
                new_value = Prompt.ask(f"Set {key_to_edit} to (y/n/skip)", choices=["y", "n", "skip"], default="skip")
                if new_value == "y":
                    plan[key_to_edit] = True
                elif new_value == "n":
                    plan[key_to_edit] = False

            elif isinstance(current_value, str) or current_value is None:
                new_value = Prompt.ask(f"Enter new value for {key_to_edit} (or leave blank to skip)", default="")
                if new_value != "":
                    plan[key_to_edit] = self.convert_input_value(new_value)

            elif isinstance(current_value, list):
                new_value = Prompt.ask(f"Enter comma-separated values for {key_to_edit} (or leave blank to skip)",
                                       default="")
                if new_value != "":
                    plan[key_to_edit] = [item.strip() for item in new_value.split(",")]

            else:
                console.print(f"[yellow]Unsupported type for key '{key_to_edit}'. Skipping.[/yellow]")

        return plan

    def _print_plan_tables(self, plan: dict) -> None:
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
            if value and value not in [None, [], ""]:
                actions_table.add_row(key, str(value))

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
            if not value or value == []:
                inactive_table.add_row(key, str(value))

        self._append_workflow_section(inactive_table, plan, active=False)
        console.print(inactive_table)

    def _append_workflow_section(self, table: Table, plan: dict, active: bool) -> None:
        if active:
            has_items = any(plan.get(k) and plan.get(k) not in [None, [], ""] for k in self.workflow_keys)
        else:
            has_items = any(not plan.get(k) or plan.get(k) == [] for k in self.workflow_keys)

        if not has_items:
            return

        table.add_row("", "")
        table.add_row("[bold]GitHub Workflows actions[/bold]", "")

        for key in self.workflow_keys:
            value = plan.get(key)
            if active:
                if value and value not in [None, [], ""]:
                    table.add_row(key, str(value))
            else:
                if not value or value == []:
                    table.add_row(key, str(value))

    @staticmethod
    def convert_input_value(value: str) -> str | None:
        if value.strip().lower() == "none":
            return None
        return value

