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
        Finalize the session: format outputs, optionally create PR, and clean up.

        Updates About section if present, collects events and builds a summary,
        then either publishes a PR (when create_fork and create_pull_request are set)
        or logs the summary. Optionally deletes the cloned repo.
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
        Collect all operation events from state artifacts (excluding generate_about).

        Args:
            state: Current workflow state.

        Returns:
            Flat list of OperationEvent instances from all artifacts.
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

        Args:
            state: Current workflow state (session_memory is updated with the summary).
            events: Operation events to summarize.

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
            Newline-separated lines describing each event.
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

        Args:
            about: Dict with keys such as description, homepage, topics.

        Returns:
            Human-readable About section text.
        """
        return (
            "You can add the following information to the `About` section of your Git repository:\n"
            f"- Description: {about.get('description', '')}\n"
            f"- Homepage: {about.get('homepage', '')}\n"
            f"- Topics: {', '.join(f'`{t}`' for t in about.get('topics', []))}\n"
        )
