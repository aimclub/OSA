import os
import yaml
from typing import Dict, List, Any

from osa_tool.github_workflow.providers.black import generate_black_formatter_workflow
from osa_tool.github_workflow.providers.unit_test import generate_unit_test_workflow
from osa_tool.readmeai.config.settings import WorkflowSettings


class GitHubWorkflowGenerator:
    """
    A generator for GitHub Action workflows that creates CI/CD pipelines for Python repositories.

    This generator can create workflows for:
    - Automated unit test execution
    - Automated code formatting using Black
    - Automated PEP 8 compliance checks (using flake8 or pylint)
    - Optional PyPI publication
    - Advanced autopep8 formatting with PR comments
    - Slash command for fixing PEP8 issues
    """

    def __init__(self, output_dir: str = ".github/workflows"):
        """
        Initialize the GitHub workflow generator.

        Args:
            output_dir: Directory where the workflow files will be saved
        """
        self.output_dir = output_dir

    def _ensure_output_dir(self) -> None:
        """Ensure the output directory exists."""
        os.makedirs(self.output_dir, exist_ok=True)

    def _write_workflow(self, filename: str, workflow: Dict[str, Any]) -> str:
        """
        Write a workflow to a YAML file.

        Args:
            filename: Name of the workflow file
            workflow: Workflow configuration as a dictionary

        Returns:
            Path to the created workflow file
        """
        self._ensure_output_dir()
        file_path = os.path.join(self.output_dir, filename)

        with open(file_path, 'w') as f:
            # Disable anchors use
            yaml.Dumper.ignore_aliases = lambda self, data: True
            yaml.dump(workflow, f, sort_keys=False, Dumper=yaml.Dumper)

        return file_path

    def generate_pep8_workflow(
        self,
        name: str = "PEP 8 Compliance",
        tool: str = "flake8",
        python_version: str = "3.10",
        args: str = "",
        branches: List[str] = ["main", "master"]
    ) -> str:
        """
        Generate a workflow for checking PEP 8 compliance.

        Args:
            name: Name of the workflow
            tool: Tool to use for PEP 8 checking (flake8 or pylint)
            python_version: Python version to use
            args: Arguments to pass to the tool
            branches: List of branches to trigger the workflow on

        Returns:
            Path to the created workflow file
        """
        if tool not in ["flake8", "pylint"]:
            raise ValueError("Tool must be either 'flake8' or 'pylint'")

        tool_command = f"{tool} {args}" if args else tool

        workflow = {
            "name": name,
            "on": {
                "push": {"branches": branches},
                "pull_request": {"branches": branches}
            },
            "jobs": {
                "lint": {
                    "name": f"Run {tool}",
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "Checkout repo",
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": f"Set up Python {python_version}",
                            "uses": "actions/setup-python@v4",
                            "with": {
                                "python-version": python_version
                            }
                        },
                        {
                            "name": "Install dependencies",
                            "run": f"pip install {tool}"
                        },
                        {
                            "name": f"Run {tool}",
                            "run": tool_command
                        }
                    ]
                }
            }
        }

        return self._write_workflow(f"{tool}.yml", workflow)

    def generate_autopep8_workflow(
        self,
        name: str = "Format python code with autopep8",
        max_line_length: int = 120,
        aggressive_level: int = 2,
        branches: List[str] = ["main", "master"]
    ) -> str:
        """
        Generate a workflow for running autopep8 and commenting on pull requests.

        Args:
            name: Name of the workflow
            max_line_length: Maximum line length for autopep8
            aggressive_level: Aggressive level for autopep8 (1 or 2)
            branches: List of branches to trigger the workflow on

        Returns:
            Path to the created workflow file
        """
        if aggressive_level not in [1, 2]:
            raise ValueError("Aggressive level must be either 1 or 2")

        aggressive_args = "--aggressive " * aggressive_level

        workflow = {
            "name": name,
            "on": {
                "pull_request": {"branches": branches}
            },
            "jobs": {
                "autopep8": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "uses": "actions/checkout@v4"
                        },
                        {
                            "name": "autopep8",
                            "id": "autopep8",
                            "uses": "peter-evans/autopep8@v2",
                            "with": {
                                "args": f"--exit-code --max-line-length {max_line_length} --recursive --in-place {aggressive_args}."
                            }
                        },
                        {
                            "name": "Find Comment",
                            "uses": "peter-evans/find-comment@v2",
                            "id": "fc",
                            "with": {
                                "issue-number": "${{ github.event.pull_request.number }}",
                                "comment-author": "github-actions[bot]"
                            }
                        },
                        {
                            "name": "Create comment if autopep8 made NO changes",
                            "if": "${{ steps.fc.outputs.comment-id == '' && steps.autopep8.outputs.exit-code != 2}}",
                            "uses": "peter-evans/create-or-update-comment@v3",
                            "with": {
                                "issue-number": "${{ github.event.pull_request.number }}",
                                "body": "Code has no PEP8 errors!"
                            }
                        },
                        {
                            "name": "Create comment if autopep8 made changes",
                            "if": "${{ steps.fc.outputs.comment-id == '' && steps.autopep8.outputs.exit-code == 2}}",
                            "uses": "peter-evans/create-or-update-comment@v3",
                            "with": {
                                "issue-number": "${{ github.event.pull_request.number }}",
                                "body": "Code in this pull request contains PEP8 errors, please write the `/fix-pep8` command in the comments below to create commit with automatic fixes."
                            }
                        },
                        {
                            "name": "Retrieve current Date & Time in Moscow TimeZone",
                            "shell": "bash",
                            "run": "echo \"TIMESTAMP=$(TZ=\":Europe/Moscow\" date -R|sed 's/.....$//')\" >> $GITHUB_ENV"
                        },
                        {
                            "name": "Update comment if NOT fixed",
                            "if": "${{ steps.fc.outputs.comment-id != '' && steps.autopep8.outputs.exit-code == 2}}",
                            "uses": "peter-evans/create-or-update-comment@v3",
                            "with": {
                                "comment-id": "${{ steps.fc.outputs.comment-id }}",
                                "edit-mode": "replace",
                                "body": "Code in this pull request **still** contains PEP8 errors, please write the `/fix-pep8` command in the comments below to create commit with automatic fixes.\n\n##### Comment last updated at ${{ env.TIMESTAMP }}"
                            }
                        },
                        {
                            "name": "Update comment if fixed",
                            "if": "${{ steps.fc.outputs.comment-id != '' && steps.autopep8.outputs.exit-code != 2}}",
                            "uses": "peter-evans/create-or-update-comment@v3",
                            "with": {
                                "comment-id": "${{ steps.fc.outputs.comment-id }}",
                                "edit-mode": "replace",
                                "body": "All PEP8 errors has been fixed, thanks :heart:\n\n##### Comment last updated at ${{ env.TIMESTAMP }}"
                            }
                        },
                        {
                            "name": "Fail if autopep8 made changes",
                            "if": "steps.autopep8.outputs.exit-code == 2",
                            "run": "exit 1"
                        }
                    ]
                }
            }
        }

        return self._write_workflow("autopep8.yml", workflow)

    def generate_fix_pep8_command_workflow(
        self,
        name: str = "fix-pep8-command",
        max_line_length: int = 120,
        aggressive_level: int = 2,
        repo_access_token: bool = True
    ) -> str:
        """
        Generate a workflow for fixing PEP8 issues when triggered by a slash command.

        Args:
            name: Name of the workflow
            max_line_length: Maximum line length for autopep8
            aggressive_level: Aggressive level for autopep8 (1 or 2)
            repo_access_token: Whether to use a repository access token

        Returns:
            Path to the created workflow file
        """
        if aggressive_level not in [1, 2]:
            raise ValueError("Aggressive level must be either 1 or 2")

        aggressive_args = "--aggressive " * aggressive_level

        workflow = {
            "name": name,
            "on": {
                "repository_dispatch": {
                    "types": ["fix-pep8-command"]
                }
            },
            "jobs": {
                "fix-pep8": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "uses": "actions/checkout@v4",
                            "with": {
                                "token": "${{ secrets.REPO_ACCESS_TOKEN }}" if repo_access_token else "${{ github.token }}",
                                "repository": "${{ github.event.client_payload.pull_request.head.repo.full_name }}",
                                "ref": "${{ github.event.client_payload.pull_request.head.ref }}"
                            }
                        },
                        {
                            "name": "autopep8",
                            "id": "autopep8",
                            "uses": "peter-evans/autopep8@v2",
                            "with": {
                                "args": f"--exit-code --max-line-length {max_line_length} --recursive --in-place {aggressive_args}."
                            }
                        },
                        {
                            "name": "Commit autopep8 changes",
                            "id": "cap8c",
                            "if": "steps.autopep8.outputs.exit-code == 2",
                            "run": "git config --global user.name 'github-actions[bot]'\ngit config --global user.email 'github-actions[bot]@users.noreply.github.com'\ngit commit -am \"Automated autopep8 fixes\"\ngit push"
                        }
                    ]
                }
            }
        }

        return self._write_workflow("fix-pep8-command.yml", workflow)

    def generate_slash_command_dispatch_workflow(
        self,
        name: str = "Slash Command Dispatch",
        commands: List[str] = ["fix-pep8"],
        permission: str = "none"
    ) -> str:
        """
        Generate a workflow for dispatching slash commands.

        Args:
            name: Name of the workflow
            commands: List of commands to dispatch
            permission: Permission level for the workflow

        Returns:
            Path to the created workflow file
        """
        workflow = {
            "name": name,
            "on": {
                "issue_comment": {
                    "types": ["created"]
                }
            },
            "permissions": {
                "contents": permission
            },
            "jobs": {
                "slashCommandDispatch": {
                    "runs-on": "ubuntu-latest",
                    "steps": [
                        {
                            "name": "Slash Command Dispatch",
                            "uses": "peter-evans/slash-command-dispatch@v3",
                            "with": {
                                "token": "${{ secrets.REPO_ACCESS_TOKEN }}",
                                "commands": ",".join(commands),
                                "permission": permission,
                                "issue-type": "pull-request"
                            }
                        }
                    ]
                }
            }
        }

        return self._write_workflow("slash-command-dispatch.yml", workflow)

    def generate_pypi_publish_workflow(
        self,
        name: str = "PyPI Publish",
        python_version: str = "3.10",
        use_poetry: bool = False,
        trigger_on_tags: bool = True,
        trigger_on_release: bool = False,
        manual_trigger: bool = True
    ) -> str:
        """
        Generate a workflow for publishing to PyPI.

        Args:
            name: Name of the workflow
            python_version: Python version to use
            use_poetry: Whether to use Poetry for packaging
            trigger_on_tags: Whether to trigger on tags
            trigger_on_release: Whether to trigger on release
            manual_trigger: Whether to allow manual triggering

        Returns:
            Path to the created workflow file
        """
        # Define the trigger
        on = {}
        if trigger_on_tags:
            on["push"] = {"tags": ["*.*.*"]}
        if trigger_on_release:
            on["release"] = {"types": ["created"]}
        if manual_trigger:
            on["workflow_dispatch"] = {}

        if not on:
            raise ValueError(
                "At least one of trigger_on_tags or trigger_on_release must be True")

        # Define the steps based on whether we're using Poetry or not
        if use_poetry:
            steps = [
                {
                    "name": "Checkout code",
                    "uses": "actions/checkout@v4"
                },
                {
                    "name": f"Set up Python {python_version}",
                    "uses": "actions/setup-python@v5",
                    "with": {
                        "python-version": python_version
                    }
                },
                {
                    "name": "Install Poetry",
                    "run": "curl -sSL https://install.python-poetry.org | python - -y"
                },
                {
                    "name": "Update PATH",
                    "run": "echo \"$HOME/.local/bin\" >> $GITHUB_PATH"
                },
                {
                    "name": "Update Poetry configuration",
                    "run": "poetry config virtualenvs.create false"
                },
                {
                    "name": "Poetry check",
                    "run": "poetry check"
                },
                {
                    "name": "Install dependencies",
                    "run": "poetry install --no-interaction"
                },
                {
                    "name": "Package project",
                    "run": "poetry build"
                },
                {
                    "name": "Publish package distributions to PyPI",
                    "uses": "pypa/gh-action-pypi-publish@release/v1"
                }
            ]
        else:
            steps = [
                {
                    "name": "Checkout code",
                    "uses": "actions/checkout@v4"
                },
                {
                    "name": f"Set up Python {python_version}",
                    "uses": "actions/setup-python@v5",
                    "with": {
                        "python-version": python_version
                    }
                },
                {
                    "name": "Install dependencies",
                    "run": "pip install setuptools wheel twine build"
                },
                {
                    "name": "Build package",
                    "run": "python -m build"
                },
                {
                    "name": "Publish package distributions to PyPI",
                    "uses": "pypa/gh-action-pypi-publish@release/v1"
                }
            ]

        workflow = {
            "name": name,
            "on": on,
            "permissions": {
                "contents": "read",
                "id-token": "write"
            },
            "jobs": {
                "pypi-publish": {
                    "name": "Upload release to PyPI",
                    "runs-on": "ubuntu-latest",
                    "environment": {
                        "name": "pypi",
                        "url": "https://pypi.org/p/${{ github.event.repository.name }}"
                    },
                    "steps": steps
                }
            }
        }

        return self._write_workflow("pypi-publish.yml", workflow)

    def generate_complete_workflow(
        self,
        settings: WorkflowSettings  # Use the imported settings object
    ) -> List[str]:
        """
        Generate a complete set of workflows.

        Args:
            settings: An object containing all workflow generation settings.

        Returns:
            List of paths to the created workflow files
        """
        created_files = []

        if settings.include_black:
            workflow = generate_black_formatter_workflow(
                branches=settings.branches)
            file_path = self._write_workflow("black.yml", workflow)
            created_files.append(file_path)

        if settings.include_tests:
            workflow = generate_unit_test_workflow(
                branches=settings.branches,
                python_versions=settings.python_versions,
                codecov_token=settings.codecov_token,
                coverage=settings.include_codecov
                )
            file_path = self._write_workflow("unit_tests.yml", workflow)
            created_files.append(file_path)

        """ Эта часть ещё в работе, пока отключил
        if settings.include_pep8:
            file_path = self.generate_pep8_workflow(
                tool=settings.pep8_tool,
                # Use the latest Python version
                python_version=settings.python_versions[-1],
                branches=settings.branches
            )
            created_files.append(file_path)

        if settings.include_autopep8:
            file_path = self.generate_autopep8_workflow(
                branches=settings.branches
            )
            created_files.append(file_path)

            if settings.include_fix_pep8:
                file_path = self.generate_fix_pep8_command_workflow()
                created_files.append(file_path)

                file_path = self.generate_slash_command_dispatch_workflow()
                created_files.append(file_path)

        if settings.include_pypi:
            file_path = self.generate_pypi_publish_workflow(
                # Use the latest Python version
                python_version=settings.python_versions[-1],
                use_poetry=settings.use_poetry
            )
            created_files.append(file_path)
        """

        return created_files


def generate_workflows_from_settings(settings: WorkflowSettings, output_dir: str) -> List[str]:
    """
    Generate workflows based on a WorkflowSettings object.

    Args:
        settings: WorkflowSettings object containing generation parameters.
        output_dir: Directory where the workflow files will be saved.

    Returns:
        List of paths to the created workflow files.
    """
    generator = GitHubWorkflowGenerator(output_dir=output_dir)
    return generator.generate_complete_workflow(settings=settings)
