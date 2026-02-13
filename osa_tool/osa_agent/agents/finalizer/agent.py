from langchain_core.output_parsers import PydanticOutputParser

from osa_tool.core.models.agent_status import AgentStatus
from osa_tool.core.models.event import OperationEvent
from osa_tool.osa_agent.agents.finalizer.models import FinalizerPullRequestSummary
from osa_tool.osa_agent.base import BaseAgent
from osa_tool.osa_agent.state import OSAState
from osa_tool.utils.logger import logger
from osa_tool.utils.prompts_builder import PromptBuilder
from osa_tool.utils.utils import rich_section, delete_repository


class FinalizerAgent(BaseAgent):
    name = "Finalizer"

    def run(self, state: OSAState) -> OSAState:
        rich_section("Finalizer Agent")
        state.active_agent = self.name

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
                logger.info("About section:\n" + about_message)

        events = self._collect_events(state)
        summary = self._summarize_events(state, events) if events else ""

        # PR or logs
        if create_pr and create_pr:
            logger.info("Publishing changes")
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
                logger.info("Summary of changes:\n" + summary)

        # Delete repository after processing
        if self.context.delete_repo:
            delete_repository(state.repo_url)

        state.status = AgentStatus.COMPLETED

        return state

    @staticmethod
    def _collect_events(state: OSAState) -> list[OperationEvent]:
        events: list[OperationEvent] = []

        for op_name, artifact in state.artifacts.items():
            if op_name == "generate_about":
                continue
            events.extend(artifact.get("events", []))

        return events

    def _summarize_events(self, state: OSAState, events: list[OperationEvent]) -> str:
        events_text = self._events_to_text(events)

        parser = PydanticOutputParser(pydantic_object=FinalizerPullRequestSummary)
        system_message = PromptBuilder.render(
            self.context.prompts.get("system_messages.pr_summarizer"),
            safe=True,
        )

        prompt = PromptBuilder.render(
            self.context.prompts.get("osa_agent.pr_summarizer"),
            events=events_text,
        )

        pr_summary: FinalizerPullRequestSummary = self.context.get_model_handler("general").run_chain(
            prompt=prompt, system_message=system_message, parser=parser
        )

        state.session_memory.append({"agent": self.name, "pr_summary": pr_summary.summary})

        return pr_summary.summary

    @staticmethod
    def _events_to_text(events: list[OperationEvent]) -> str:
        lines = []
        for e in events:
            line = f"- {e.kind.value}: {e.target}"
            if e.data:
                line += f" ({', '.join(f'{k}={v}' for k, v in e.data.items())})"
            lines.append(line)
        return "\n".join(lines)

    @staticmethod
    def _format_about_message(about: dict) -> str:
        return (
            "You can add the following information to the `About` section of your Git repository:\n"
            f"- Description: {about.get('description', '')}\n"
            f"- Homepage: {about.get('homepage', '')}\n"
            f"- Topics: {', '.join(f'`{t}`' for t in about.get('topics', []))}\n"
        )
