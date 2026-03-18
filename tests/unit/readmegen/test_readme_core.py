from unittest.mock import MagicMock, patch

from osa_tool.core.models.event import EventKind, OperationEvent
from osa_tool.operations.docs.readme_generation.readme_core import ReadmeAgent


@patch("osa_tool.operations.docs.readme_generation.readme_core.build_readme_graph")
@patch("osa_tool.operations.docs.readme_generation.readme_core.ReadmeContext")
def test_readme_agent_standard_mode(
    mock_context_cls,
    mock_build_graph,
    mock_config_manager,
    mock_repository_metadata,
):
    """Graph is invoked and result dict has correct format."""
    mock_graph = MagicMock()
    mock_build_graph.return_value = mock_graph
    mock_graph.invoke.return_value = {
        "events": [OperationEvent(kind=EventKind.GENERATED, target="README.md")],
    }

    agent = ReadmeAgent(
        config_manager=mock_config_manager,
        metadata=mock_repository_metadata,
        attachment=None,
    )
    result = agent.generate_readme()

    mock_build_graph.assert_called_once_with(mock_context_cls.return_value)
    mock_graph.invoke.assert_called_once()
    assert result["result"]["file"] == "README.md"
    assert result["result"]["path"] == agent.file_to_save
    assert len(result["events"]) == 1
    assert result["events"][0].kind == EventKind.GENERATED


@patch("osa_tool.operations.docs.readme_generation.readme_core.build_readme_graph")
@patch("osa_tool.operations.docs.readme_generation.readme_core.ReadmeContext")
def test_readme_agent_with_article(
    mock_context_cls,
    mock_build_graph,
    mock_config_manager,
    mock_repository_metadata,
):
    """Attachment is passed through to ReadmeState."""
    mock_graph = MagicMock()
    mock_build_graph.return_value = mock_graph
    mock_graph.invoke.return_value = {
        "events": [OperationEvent(kind=EventKind.GENERATED, target="README.md")],
    }

    article_path = "/path/to/article.pdf"
    agent = ReadmeAgent(
        config_manager=mock_config_manager,
        metadata=mock_repository_metadata,
        attachment=article_path,
    )
    result = agent.generate_readme()

    invoked_state = mock_graph.invoke.call_args[0][0]
    assert invoked_state.attachment == article_path
    assert result["result"] is not None


@patch("osa_tool.operations.docs.readme_generation.readme_core.build_readme_graph")
@patch("osa_tool.operations.docs.readme_generation.readme_core.ReadmeContext")
def test_readme_agent_with_active_request(
    mock_context_cls,
    mock_build_graph,
    mock_config_manager,
    mock_repository_metadata,
):
    """active_request maps to ReadmeState.user_request."""
    mock_graph = MagicMock()
    mock_build_graph.return_value = mock_graph
    mock_graph.invoke.return_value = {"events": []}

    agent = ReadmeAgent(
        config_manager=mock_config_manager,
        metadata=mock_repository_metadata,
        active_request="Improve the installation section",
    )
    agent.generate_readme()

    invoked_state = mock_graph.invoke.call_args[0][0]
    assert invoked_state.user_request == "Improve the installation section"


@patch("osa_tool.operations.docs.readme_generation.readme_core.build_readme_graph")
@patch("osa_tool.operations.docs.readme_generation.readme_core.ReadmeContext")
def test_readme_agent_error_handling(
    mock_context_cls,
    mock_build_graph,
    mock_config_manager,
    mock_repository_metadata,
):
    """On exception, returns result=None with FAILED event."""
    mock_build_graph.return_value.invoke.side_effect = RuntimeError("LLM timeout")

    agent = ReadmeAgent(
        config_manager=mock_config_manager,
        metadata=mock_repository_metadata,
    )
    result = agent.generate_readme()

    assert result["result"] is None
    assert len(result["events"]) == 1
    assert result["events"][0].kind == EventKind.FAILED
    assert "LLM timeout" in result["events"][0].data["error"]
