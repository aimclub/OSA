from argparse import Namespace
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from osa_tool.run import main
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
        article_date=None,
        ignore_list=None,
        incremental=False,
        target_files=None,
    )


@pytest.fixture
def run_environment(run_args):
    """Patch everything `main` talks to and yield the arguments with the fake Git agent."""
    git_agent = MagicMock()
    git_agent.article_date = None

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


def test_main_skips_fork_and_pull_request_for_article_date(run_environment):
    # Arrange
    args, git_agent = run_environment
    args.article_date = "2021-01-01"
    git_agent.article_date = datetime(2021, 1, 1, tzinfo=timezone.utc)

    # Act
    with pytest.raises(SystemExit) as exit_info:
        main()

    # Assert
    assert exit_info.value.code == 0
    git_agent.star_repository.assert_not_called()
    git_agent.create_fork.assert_not_called()
    git_agent.create_and_checkout_branch.assert_not_called()
    git_agent.create_pull_request.assert_not_called()
    git_agent.clone_repository.assert_called_once()
