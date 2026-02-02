from typing import Optional

from pydantic import BaseModel
from rich.console import Console

console = Console()


class InitialChatInput(BaseModel):
    repo_url: str
    user_request: str
    attachment: Optional[str] = None


class ClarifyChatInput(BaseModel):
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


def clarify_user_input() -> ClarifyChatInput:
    console.print("\n[bold yellow]Intent not clear. Please refine your request.[/]\n")

    user_request = ""
    while not user_request:
        user_request = console.input("[cyan]Clarified user request:[/] ").strip()
        if not user_request:
            console.print("[red]User request is required![/]")

    attachment = console.input("[cyan]Attachment (optional, single value):[/] ").strip()
    # Convert empty string → None
    if not attachment:
        attachment = None

    return ClarifyChatInput(
        user_request=user_request,
        attachment=attachment,
    )
