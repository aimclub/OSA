from langchain_core.output_parsers import PydanticOutputParser

from osa_tool.core.models.agent_status import AgentStatus
from osa_tool.core.models.event import OperationEvent
from osa_tool.osa_agent.agents.finalizer.models import FinalizerPullRequestSummary
from osa_tool.osa_agent.base import BaseAgent
from osa_tool.osa_agent.state import OSAState
from osa_tool.utils.logger import logger
from osa_tool.utils.utils import rich_section, delete_repository


class FinalizerAgent(BaseAgent):
    """
    Agent responsible for wrapping up the workflow.
    """


    name = "Finalizer"

    def run(self, state: OSAState) -> OSAState:
        """
        Finalize the session: format outputs, optionally create a pull request, and clean up.
        
        Updates the repository's About section if present, collects operation events, and builds a summary.
        Depending on configuration, it either publishes a pull request (when both a fork and pull request are requested) or logs the summary.
        Optionally deletes the locally cloned repository after processing.
        
        Why:
        This method serves as the concluding step in the workflow, ensuring that all generated artifacts are properly formatted and delivered. It centralizes the decision-making for whether to create a pull request or simply log results, and handles cleanup to avoid leaving temporary files.
        
        Args:
            state: The current workflow state containing artifacts, session memory, and repository details.
        
        Returns:
            The updated workflow state with status set to COMPLETED.
        
        Behavior details:
        - If an About section artifact exists, it is formatted. When a fork is requested, the About section is updated in the repository; otherwise, it is logged.
        - Operation events are collected (excluding those from the 'generate_about' operation) and summarized.
        - When both a fork and a pull request are requested, changes are committed and pushed, and a pull request is created with the summary and About text as the body.
        - If a pull request is not created, the summary is logged instead.
        - If configured, the local clone of the repository is deleted to free disk space.
        - The state's status is updated to COMPLETED and session memory statistics are logged.
        """
        rich_section("Finalizer Agent")
        state.active_agent = self.name
        logger.debug("Finalizer started")

        create_fork = self.context.create_fork
        create_pr = self.context.create_pull_request

        # About - special case, no summarization
        about_artifact = state.artifacts.get("generate_about")
        about_message = ""
        if about_artifact:
            about_message = self._format_about_message(about_artifact.get("result", {}))

            if create_fork:
                self.context.git_agent.update_about_section(about_artifact.get("result", {}))

            if not create_pr:
                logger.info("About section: %s", about_message)

        events = self._collect_events(state)
        summary = self._summarize_events(state, events) if events else ""

        # PR or logs
        if create_fork and create_pr:
            logger.info("Publishing changes and creating pull request")
            changes = self.context.git_agent.commit_and_push_changes(force=True)

            pr_body = summary

            if about_message:
                pr_body += "\n\n---\n\n" + about_message

            self.context.git_agent.create_pull_request(
                body=pr_body,
                changes=changes,
            )
        else:
            if summary:
                logger.info("Summary of changes: %s", summary)

        # Delete repository after processing
        if self.context.delete_repo:
            delete_repository(state.repo_url)
            logger.info("Cloned repository deleted: %s", state.repo_url)

        state.status = AgentStatus.COMPLETED
        logger.debug("Session memory entries: %s", len(state.session_memory))

        return state

    @staticmethod
    def _collect_events(state: OSAState) -> list[OperationEvent]:
        """
        Collect all operation events from state artifacts, excluding those from the 'generate_about' operation.
        
        This method aggregates events logged during the workflow's execution, which are stored within each artifact. The 'generate_about' operation is specifically excluded because its events are typically meta-information or summaries that are not intended for the same downstream processing as the core operational events.
        
        Args:
            state: The current workflow state containing all artifacts.
        
        Returns:
            A flat list of OperationEvent instances collected from all relevant artifacts.
        """
        events: list[OperationEvent] = []

        for op_name, artifact in state.artifacts.items():
            if op_name == "generate_about":
                continue
            events.extend(artifact.get("events", []))

        return events

    def _summarize_events(self, state: OSAState, events: list[OperationEvent]) -> str:
        """
        Use the LLM to produce a PR summary from the collected events.
        
        The method converts the provided operation events into a formatted text, then uses a prompt template and a system message to instruct an LLM to generate a structured pull request summary. The resulting summary is stored in the session memory for tracking and returned for use in the PR body or logging.
        
        Args:
            state: Current workflow state. The session_memory attribute is updated with the generated summary.
            events: List of operation events to summarize. Each event describes an operation performed during the workflow.
        
        Returns:
            Summary string for the PR body or logging.
        """
        events_text = self._events_to_text(events)

        parser = PydanticOutputParser(pydantic_object=FinalizerPullRequestSummary)
        system_message = self._render("system_messages.pr_summarizer", safe=True)
        prompt = self._render("osa_agent.pr_summarizer", events=events_text)

        pr_summary: FinalizerPullRequestSummary = self._run_llm(prompt, parser, system_message)

        state.session_memory.append({"agent": self.name, "pr_summary": pr_summary.summary})

        return pr_summary.summary

    @staticmethod
    def _events_to_text(events: list[OperationEvent]) -> str:
        """
        Convert operation events to a single text block for the LLM.
        
        Args:
            events: List of OperationEvent instances.
        
        Returns:
            Newline-separated lines describing each event. Each line is formatted as:
            "- <event_kind>: <target> (<key1>=<value1>, <key2>=<value2>, ...)" if data is present,
            or "- <event_kind>: <target>" if no data is associated. The event_kind is the string value
            of the OperationEvent's kind attribute, and target is its target attribute. Additional
            data items are appended in parentheses as comma-separated key-value pairs.
        """
        lines = []
        for e in events:
            line = "- %s: %s" % (e.kind.value, e.target)
            if e.data:
                line += " (%s)" % ", ".join("%s=%s" % (k, v) for k, v in e.data.items())
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _format_about_message(about: dict) -> str:
        """
        Format the About section content for display or PR body.
        
        This method generates a human-readable text block that can be inserted into a repository's `About` section or a pull request body. It extracts key metadata from the provided dictionary and formats it into a clear, bulleted list.
        
        Args:
            about: Dictionary containing repository metadata. Expected keys include 'description' (a short project summary), 'homepage' (the project's main URL), and 'topics' (a list of repository tags or keywords). Missing keys are handled gracefully with default empty values.
        
        Returns:
            Human-readable About section text as a formatted string. The output includes a header line followed by bullet points for description, homepage, and topics (each topic is formatted as an inline code block).
        """
        return (
            "You can add the following information to the `About` section of your Git repository:\n"
            f"- Description: {about.get('description', '')}\n"
            f"- Homepage: {about.get('homepage', '')}\n"
            f"- Topics: {', '.join(f'`{t}`' for t in about.get('topics', []))}\n"
        )
