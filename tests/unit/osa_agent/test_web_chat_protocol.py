import io
import json
from argparse import Namespace
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from osa_tool.core.models.agent_status import AgentStatus
from osa_tool.core.models.task import Task, TaskStatus
from osa_tool.osa_agent.agents.reviewer.agent import ReviewerAgent
from osa_tool.osa_agent.state import OSAState
from osa_tool.web_chat import ChatProtocolError, JsonLineChatIO, _run, use_web_questions
from osa_tool.ui.input_for_chat import wait_for_user_clarification


class AnswerSource:
    def __init__(self, sink: io.StringIO):
        self.sink = sink
        self.calls = 0

    def readline(self, limit: int) -> str:
        self.calls += 1
        question = next(
            event
            for event in (json.loads(line) for line in self.sink.getvalue().splitlines())
            if event["type"] == "question"
        )
        if self.calls == 1:
            return json.dumps({"type": "answer", "id": "wrong", "values": {"accept": "yes"}}) + "\n"
        return json.dumps({"type": "answer", "id": question["id"], "values": {"accept": "no"}}) + "\n"


def test_start_requires_repository_and_request():
    io_adapter = JsonLineChatIO(io.StringIO('{"type":"start","repository":"","request":"x"}\n'), io.StringIO())
    try:
        io_adapter.read_start()
    except ChatProtocolError as exc:
        assert str(exc) == "Repository is required"
    else:
        raise AssertionError("Missing repository was accepted")


def test_terminal_mode_still_collects_terminal_input():
    from osa_tool.run_chat import main

    with (
        patch("sys.argv", ["run_chat"]),
        patch("osa_tool.run_chat.collect_user_input", side_effect=RuntimeError("terminal prompt")),
        pytest.raises(RuntimeError, match="terminal prompt"),
    ):
        main()


def test_web_questions_validate_ids_and_preserve_terminal_fallback():
    sink = io.StringIO()
    io_adapter = JsonLineChatIO(AnswerSource(sink), sink)
    state = OSAState(
        session_id="test",
        clarification_required=True,
        clarification_agent="Reviewer",
        clarification_type="review",
        clarification_payload={
            "question": "Approve?",
            "fields": [{"name": "accept", "prompt": "Approve?", "required": True}],
        },
    )
    with use_web_questions(io_adapter.ask):
        assert wait_for_user_clarification(state) == {"accept": "no"}
    events = [json.loads(line) for line in sink.getvalue().splitlines()]
    assert [event["type"] for event in events] == ["review", "question", "error"]
    assert events[-1]["recoverable"] is True


def test_rejected_last_review_cycle_stops_without_approval():
    state = OSAState(session_id="test", review_cycle_count=2, max_review_cycles=3)
    decision = SimpleNamespace(
        requires_new_intent=False,
        requires_new_task_scope=False,
        new_intent=None,
        new_task_scope=None,
        reviewer_summary="Needs changes",
    )
    agent = ReviewerAgent(SimpleNamespace())
    with (
        patch(
            "osa_tool.osa_agent.agents.reviewer.agent.wait_for_user_clarification",
            side_effect=[{"accept": "no"}, {"feedback": "Improve the output"}],
        ),
        patch.object(agent, "_analyze_feedback_with_llm", return_value=decision),
    ):
        result = agent.run(state)
    assert result.review_cycles_exhausted is True
    assert result.approval is False
    assert result.status == AgentStatus.STOPPED


def test_web_run_emits_structured_completion_without_terminal_input():
    source = io.StringIO(
        json.dumps(
            {
                "type": "start",
                "repository": "https://github.com/example/repo",
                "request": "Improve README",
                "attachment": None,
            }
        )
        + "\n"
    )
    sink = io.StringIO()
    io_adapter = JsonLineChatIO(source, sink)
    completed = OSAState(
        session_id="test",
        active_agent="Finalizer",
        status=AgentStatus.COMPLETED,
        final_summary="README updated",
        plan=[
            Task(
                id="generate_readme",
                description="Create README",
                status=TaskStatus.COMPLETED,
                result={"files": ["README.md"]},
            )
        ],
    )
    graph = SimpleNamespace(stream=lambda state, stream_mode: iter([completed.model_dump()]))
    args = Namespace(output=None, log_dir="/tmp/osa-chat-tests", delete_dir=False)
    with (
        patch("osa_tool.web_chat.setup_logging"),
        patch("osa_tool.web_chat.ConfigManager", return_value=object()),
        patch("osa_tool.web_chat.initialize_git_platform", return_value=(object(), object())),
        patch("osa_tool.web_chat.resolve_publishing_options", return_value=(False, False)),
        patch("osa_tool.web_chat.OSAConfig", return_value=object()),
        patch("osa_tool.web_chat.AgentContext", return_value=object()),
        patch("osa_tool.web_chat.build_graph", return_value=graph),
    ):
        assert _run(args, io_adapter) == 0
    events = [json.loads(line) for line in sink.getvalue().splitlines()]
    assert [event["type"] for event in events] == ["started", "progress", "completed"]
    assert events[-1]["summary"] == "README updated"
    assert events[-1]["tasks"] == [{"id": "generate_readme", "status": "completed", "result": {"files": ["README.md"]}}]
    assert events[-1]["pull_request_url"] is None
