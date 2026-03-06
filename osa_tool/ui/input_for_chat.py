from typing import Optional

from pydantic import BaseModel
from rich.console import Console

from osa_tool.osa_agent.state import OSAState

console = Console()


class InitialChatInput(BaseModel):
    repo_url: str
    user_request: str
    attachment: Optional[str] = None


def collect_user_input() -> InitialChatInput:
    """
    Collect required interactive input from the user via console.
    repo_url and user_request are required, attachment is optional.
    """
    console.print("\n[bold green]Enter the parameters for analysis:[/]\n")

    repo_url = ""
    while not repo_url:
        repo_url = console.input("[cyan]Repository URL:[/] ").strip()  # todo add repo_url validation
        if not repo_url:
            console.print("[red]Repository URL is required![/]")

    user_request = ""
    while not user_request:
        user_request = console.input("[cyan]User request:[/] ").strip()
        if not user_request:
            console.print("[red]User request is required![/]")

    attachment = console.input(
        "[cyan]Attachment (optional, single value):[/] "
    ).strip()  # todo add attachment path validation

    # Convert empty string → None
    if not attachment:
        attachment = None

    return InitialChatInput(
        repo_url=repo_url,
        user_request=user_request,
        attachment=attachment,
    )


def wait_for_user_clarification(state: OSAState) -> dict:
    """
    Universal mechanism for requesting clarification.
    Supports multiple fields defined by the agent.
    """

    if not state.clarification_required:
        raise RuntimeError("wait_for_user_clarification called but no clarification was requested")

    payload = state.clarification_payload or {}
    question = payload.get("question", "Additional information required:")
    fields = payload.get("fields", [])

    console.print(f"\n[bold yellow]{question}[/]\n")

    answers = {}

    for field in fields:
        name = field["name"]
        prompt = field["prompt"]
        required = field.get("required", False)

        while True:
            value = console.input(f"[cyan]{prompt}[/] ").strip()
            if value or not required:
                break
            console.print("[red]This field is required![/]")

        answers[name] = value if value else None

    return answers
