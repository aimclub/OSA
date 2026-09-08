from argparse import Namespace
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from osa_tool.run import initialize_git_platform, main
from osa_tool.scheduler.plan import Plan


@pytest.fixture
def run_args():
    """Minimal set of arguments needed to walk through `main` without running any task."""
    return Namespace(
        repository="https://github.com/aimclub/OSA",
        no_fork=False,
        no_pull_request=False,
        output=None,
        web_mode=True,
        based_on_date=None,
        ignore_list=None,
        incremental=False,
        target_files=None,
    )


@pytest.fixture
def run_environment(run_args):
    """Patch everything `main` talks to and yield the arguments with the fake Git agent."""
    git_agent = MagicMock()
    git_agent.based_on_date = None

    parser = MagicMock()
    parser.parse_args.return_value = run_args

    scheduler = MagicMock()
    scheduler.plan = Plan({})

    with (
        patch("osa_tool.run.build_parser_from_yaml", return_value=parser),
        patch("osa_tool.run.setup_logging"),
        patch("osa_tool.run.ConfigManager"),
        patch("osa_tool.run.initialize_git_platform", return_value=(git_agent, MagicMock())),
        patch("osa_tool.run.SourceRank"),
        patch("osa_tool.run.ModeScheduler", return_value=scheduler),
    ):
        yield run_args, git_agent


def test_main_creates_fork_and_pull_request_by_default(run_environment):
    # Arrange
    _, git_agent = run_environment

    # Act
    with pytest.raises(SystemExit) as exit_info:
        main()

    # Assert
    assert exit_info.value.code == 0
    git_agent.create_fork.assert_called_once()
    git_agent.create_and_checkout_branch.assert_called_once()
    git_agent.create_pull_request.assert_called_once()


def test_main_skips_fork_and_pull_request_for_based_on_date(run_environment):
    # Arrange
    args, git_agent = run_environment
    args.based_on_date = "2021-01-01"
    git_agent.based_on_date = datetime(2021, 1, 1, tzinfo=timezone.utc)

    # Act
    with patch("osa_tool.run.logger") as mock_logger:
        with pytest.raises(SystemExit) as exit_info:
            main()

    # Assert
    assert exit_info.value.code == 0
    git_agent.star_repository.assert_not_called()
    git_agent.create_fork.assert_not_called()
    git_agent.create_and_checkout_branch.assert_not_called()
    git_agent.create_pull_request.assert_not_called()
    git_agent.clone_repository.assert_called_once()

    warnings = [call.args[0] for call in mock_logger.warning.call_args_list]
    assert any("NO FORK" in message and "NO PULL REQUEST" in message for message in warnings)
    assert any("2021-01-01" in message for message in warnings)


def test_initialize_git_platform_passes_based_on_date_from_config(run_args):
    # Arrange
    config_manager = MagicMock()
    config_manager.config.git.based_on_date = datetime(2021, 1, 1, tzinfo=timezone.utc)
    config_manager.config.git.osa_branch_name = "osa_tool"
    run_args.branch = None
    run_args.author = None

    # Act
    with (
        patch("osa_tool.run.GitHubAgent") as mock_github_agent,
        patch("osa_tool.run.GitHubWorkflowManager"),
    ):
        initialize_git_platform(run_args, config_manager)

    # Assert
    assert mock_github_agent.call_args.kwargs["based_on_date"] == datetime(2021, 1, 1, tzinfo=timezone.utc)
