from typing import Optional

from pydantic import BaseModel
from rich.console import Console

from osa_tool.osa_agent.state import OSAState

console = Console()


class InitialChatInput(BaseModel):
    """
    Initializes the chat input for a repository analysis session.
    
        Class Attributes:
        - repo_url: The URL of the repository to be analyzed.
        - user_request: The user's specific request or query regarding the repository.
        - attachment: Any additional files or data attached to the request.
    
        This class serves as a container for the initial input parameters needed to start a repository analysis. It holds the repository location, the user's query, and any supplementary attachments to facilitate the analysis process.
    """

    repo_url: str
    user_request: str
    attachment: Optional[str] = None


def collect_user_input() -> InitialChatInput:
    """
    Collect required interactive input from the user via console.
    Prompts for a repository URL and a user request, which are mandatory.
    Optionally accepts an attachment path.
    Empty input for the attachment is converted to None.
    Returns an InitialChatInput object containing the collected values.
    
    Args:
        repo_url: The URL of the repository to analyze.
        user_request: The user's request or query for the analysis.
        attachment: An optional file path or single value attachment; can be left empty.
    
    Returns:
        An InitialChatInput instance populated with the provided repo_url, user_request, and attachment.
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
    Universal mechanism for requesting clarification from the user.
    Supports multiple fields defined by the agent.
    
    This method is called when the agent determines that additional user input is needed to proceed.
    It prompts the user for each required field and collects their responses.
    
    Args:
        state: The current OSAState object, which must indicate that clarification is required and contain the clarification payload.
    
    Returns:
        A dictionary mapping each field name to the user's provided answer (or None if the field was optional and left empty).
    
    Raises:
        RuntimeError: If called when no clarification has been requested (i.e., `state.clarification_required` is False).
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
