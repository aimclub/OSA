import os
from abc import ABC, abstractmethod
from typing import List, Optional

import yaml

from osa_tool.config.settings import WorkflowSettings
from osa_tool.scheduler.plan import Plan
from osa_tool.utils.utils import osa_project_root


class WorkflowGenerator(ABC):
    def __init__(self, output_dir: str):
        """
        Initialize the CICD files generator.

        Args:
            output_dir: Directory where the CICD files will be saved.
        """
        self.output_dir = output_dir

    def _ensure_output_dir(self) -> None:
        """Ensure the output directory exists."""
        os.makedirs(self.output_dir, exist_ok=True)

    @abstractmethod
    def load_template(self, template_name: str) -> str:
        """
        Load a template file content as a string.

        Args:
            template_name: Template file name.

        Returns:
            str: Contents of the template file.
        """
        pass

    @abstractmethod
    def generate_black_formatter(self) -> None:
        """Generate black formatter part."""
        pass

    @abstractmethod
    def generate_unit_test(self) -> None:
        """Generate unit test part."""
        pass

    @abstractmethod
    def generate_pep8(self) -> None:
        """Generate PEP8 checking part."""
        pass

    @abstractmethod
    def generate_autopep8(self) -> None:
        """Generate auto-PEP8 fixing part."""
        pass

    @abstractmethod
    def generate_fix_pep8_command(self) -> None:
        """Generate part for fixing PEP8 issues."""
        pass

    @abstractmethod
    def generate_slash_command_dispatch(self) -> None:
        """Generate part for slash command dispatch."""
        pass

    @abstractmethod
    def generate_pypi_publish(self) -> None:
        """Generate PyPI publish part."""
        pass

    @abstractmethod
    def generate_selected_jobs(self, settings: WorkflowSettings, plan: Plan) -> List[str]:
        """Generate selected jobs based on settings.

        Args:
            settings: CI/CD specific settings extracted from the config.

        Returns:
            List[str]: List of paths to generated files.
        """
        pass


class GitHubWorkflowGenerator(WorkflowGenerator):
    def load_template(self, template_name: str) -> str:
        """
        Load a template file content as a string.

        Args:
            template_name: Template file name.

        Returns:
            str: Contents of the template file.
        """
        template_path = os.path.join(
            osa_project_root(),
            "config",
            "templates",
            "workflow",
            "github_gitverse",
            template_name,
        )
        with open(template_path, "r", encoding="utf-8") as file:
            return file.read()

    def generate_black_formatter(
        self,
        name: str = "Black Formatter",
        job_name: str = "Lint",
        branches: List[str] = [],
        black_options: str = "--check --diff",
        src: str = ".",
        use_pyproject: bool = False,
        version: Optional[str] = None,
        jupyter: bool = False,
        python_version: Optional[str] = None,
    ) -> str:
        """
        Create a GitHub Actions workflow for running the Black code formatter
        using the official Black action.

        Args:
            name: Workflow name (default: "Black Formatter").
            job_name: Job name inside the workflow (default: "Lint").
            branches: List of branches to trigger on (default: None, triggers on all branches).
            black_options: Options to pass to Black formatter.
            src: Source directory to format.
            use_pyproject: Whether to use pyproject.toml config.
            version: Specific Black version to use.
            jupyter: Whether to format Jupyter notebooks.
            python_version: Python version to setup.

        Returns:
            str: Path to the generated file.
        """
        steps = [{"name": "Checkout repo", "uses": "actions/checkout@v4"}]
        if use_pyproject or python_version:
            steps.append(
                {
                    "name": "Set up Python",
                    "uses": "actions/setup-python@v5",
                    "with": {"python-version": python_version or "3.11"},
                }
            )

        black_step = {
            "name": "Run Black",
            "uses": "psf/black@stable",
            "with": {"options": black_options, "src": src, "jupyter": str(jupyter).lower()},
        }
        if use_pyproject:
            black_step["with"]["use_pyproject"] = "true"
        if version:
            black_step["with"]["version"] = version
        steps.append(black_step)

        steps_yaml = yaml.dump(steps, default_flow_style=False, indent=1)
        steps_yaml = steps_yaml.replace("\n  ", "\n        ")
        steps_yaml = steps_yaml.replace("\n- ", "\n      - ")

        on_section = {}
        if branches:
            on_section = {"push": {"branches": branches}, "pull_request": {"branches": branches}}
        else:
            on_section = ["push", "pull_request"]

        template = self.load_template("black.yml")
        rendered = template.format(
            name=name,
            on_section=yaml.dump(on_section, default_flow_style=False).rstrip(),
            job_name=job_name,
            steps=steps_yaml,
        )

        file_path = os.path.join(self.output_dir, "black.yml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(rendered)

        return file_path

    def generate_unit_test(
        self,
        name: str = "Unit Tests",
        python_versions: List[str] = ["3.9", "3.10"],
        os_list: List[str] = ["ubuntu-latest"],
        dependencies_command: str = "pip install -r requirements.txt",
        test_command: str = "pytest tests/",
        branches: List[str] = [],
        coverage: bool = True,
        timeout_minutes: int = 15,
        codecov_token: bool = False,
    ) -> str:
        """
        Generate a GitHub Actions workflow for running unit tests.

        Args:
            name: Name of the workflow.
            python_versions: List of Python versions to test against.
            os_list: List of operating systems to test on.
            dependencies_command: Command to install dependencies.
            test_command: Command to run tests.
            branches: List of branches to trigger the workflow on.
            coverage: Whether to include code coverage reporting.
            timeout_minutes: Maximum time in minutes for the job to run.
            codecov_token: Whether to use a Codecov token for uploading coverage.

        Returns:
            str: Path to the generated file.
        """
        if branches:
            on_section = {
                "push": {"branches": branches},
                "pull_request": {"branches": branches},
                "workflow_dispatch": {},
            }
        else:
            on_section = ["push", "pull_request", "workflow_dispatch"]

        codecov_step = ""
        if coverage:
            codecov_step = """  - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v4"""
            if codecov_token:
                codecov_step += """
        with:
          token: ${{ secrets.CODECOV_TOKEN }}"""

        template = self.load_template("unit_test.yml")

        rendered = template.format(
            name=name,
            on_section=yaml.dump(on_section, default_flow_style=False).rstrip(),
            timeout_minutes=timeout_minutes,
            os_list=os_list,
            python_versions=python_versions,
            dependencies_command=dependencies_command,
            test_command=test_command,
            codecov_step=codecov_step,
        )

        file_path = os.path.join(self.output_dir, "unit_test.yml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(rendered)

        return file_path

    def generate_pep8(
        self,
        name: str = "PEP 8 Compliance",
        tool: str = "flake8",
        python_version: str = "3.10",
        args: str = "",
        branches: List[str] = ["main", "master"],
    ) -> str:
        """
        Generate a workflow for checking PEP 8 compliance.

        Args:
            name: Name of the workflow.
            tool: Tool to use for PEP 8 checking (flake8 or pylint).
            python_version: Python version to use.
            args: Arguments to pass to the tool.
            branches: List of branches to trigger the workflow on.

        Returns:
            str: Path to the generated file.
        """
        if branches:
            on_section = {"push": {"branches": branches}, "pull_request": {"branches": branches}}
        else:
            on_section = ["push", "pull_request"]

        if tool not in ["flake8", "pylint"]:
            raise ValueError("Tool must be either 'flake8' or 'pylint'")

        tool_command = f"{tool} {args}" if args else tool

        template = self.load_template("pep8.yml")
        rendered = template.format(
            name=name,
            on_section=yaml.dump(on_section, default_flow_style=False).rstrip(),
            tool=tool,
            python_version=python_version,
            tool_command=tool_command,
        )

        file_path = os.path.join(self.output_dir, "pep8.yml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(rendered)

        return file_path

    def generate_autopep8(
        self,
        name: str = "Format python code with autopep8",
        max_line_length: int = 120,
        aggressive_level: int = 2,
        branches: List[str] = ["main", "master"],
    ) -> str:
        """
        Generate a workflow for running autopep8 and commenting on pull requests.

        Args:
            name: Name of the workflow.
            max_line_length: Maximum line length for autopep8.
            aggressive_level: Aggressive level for autopep8 (1 or 2).
            branches: List of branches to trigger the workflow on.

        Returns:
            str: Path to the generated file.
        """
        if branches:
            on_section = {"pull_request": {"branches": branches}}
        else:
            on_section = ["pull_request"]

        if aggressive_level not in [1, 2]:
            raise ValueError("Aggressive level must be either 1 or 2")

        aggressive_args = "--aggressive " * aggressive_level

        template = self.load_template("autopep8.yml")
        rendered = template.format(
            name=name,
            on_section=yaml.dump(on_section, default_flow_style=False).rstrip(),
            max_line_length=max_line_length,
            aggressive_args=aggressive_args,
        )

        file_path = os.path.join(self.output_dir, "autopep8.yml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(rendered)

        return file_path

    def generate_fix_pep8_command(
        self,
        name: str = "fix-pep8-command",
        max_line_length: int = 120,
        aggressive_level: int = 2,
        repo_access_token: bool = True,
    ) -> str:
        """
        Generate a workflow for fixing PEP8 issues when triggered by a slash command.

        Args:
            name: Name of the workflow.
            max_line_length: Maximum line length for autopep8.
            aggressive_level: Aggressive level for autopep8 (1 or 2).
            repo_access_token: Whether to use a repository access token.

        Returns:
            str: Path to the generated file.
        """
        if aggressive_level not in [1, 2]:
            raise ValueError("Aggressive level must be either 1 or 2")

        aggressive_args = "--aggressive " * aggressive_level

        template = self.load_template("fix_pep8.yml")
        rendered = template.format(
            name=name,
            token="${{ secrets.REPO_ACCESS_TOKEN }}" if repo_access_token else "${{ github.token }}",
            max_line_length=max_line_length,
            aggressive_args=aggressive_args,
        )

        file_path = os.path.join(self.output_dir, "fix_pep8.yml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(rendered)

        return file_path

    def generate_slash_command_dispatch(
        self,
        name: str = "Slash Command Dispatch",
        commands: List[str] = ["fix-pep8"],
        permission: str = "none",
    ) -> str:
        """
        Generate a workflow for dispatching slash commands.

        Args:
            name: Name of the workflow.
            commands: List of commands to dispatch.
            permission: Permission level for the workflow.

        Returns:
            str: Path to the generated file.
        """
        template = self.load_template("slash_command_dispatch.yml")
        rendered = template.format(
            name=name,
            permission=permission,
            commands=",".join(commands),
        )

        file_path = os.path.join(self.output_dir, "slash_command_dispatch.yml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(rendered)

        return file_path

    def generate_pypi_publish(
        self,
        name: str = "PyPI Publish",
        python_version: str = "3.10",
        use_poetry: bool = False,
        trigger_on_tags: bool = True,
        trigger_on_release: bool = False,
        manual_trigger: bool = True,
    ) -> str:
        """
        Generate a workflow for publishing to PyPI.

        Args:
            name: Name of the workflow.
            python_version: Python version to use.
            use_poetry: Whether to use Poetry for packaging.
            trigger_on_tags: Whether to trigger on tags.
            trigger_on_release: Whether to trigger on release.
            manual_trigger: Whether to allow manual triggering.

        Returns:
            str: Path to the generated file.
        """
        on_section = {}
        if trigger_on_tags:
            on_section["push"] = {"tags": ["*.*.*"]}
        if trigger_on_release:
            on_section["release"] = {"types": ["created"]}
        if manual_trigger:
            on_section["workflow_dispatch"] = {}

        if not on_section:
            raise ValueError("At least one of trigger_on_tags or trigger_on_release must be True")

        if use_poetry:
            steps = [
                {
                    "name": "Install Poetry",
                    "run": "curl -sSL https://install.python-poetry.org | python - -y",
                },
                {
                    "name": "Update PATH",
                    "run": 'echo "$HOME/.local/bin" >> $GITHUB_PATH',
                },
                {
                    "name": "Update Poetry configuration",
                    "run": "poetry config virtualenvs.create false",
                },
                {"name": "Poetry check", "run": "poetry check"},
                {
                    "name": "Install dependencies",
                    "run": "poetry install --no-interaction",
                },
                {"name": "Package project", "run": "poetry build"},
                {
                    "name": "Publish package distributions to PyPI",
                    "uses": "pypa/gh-action-pypi-publish@release/v1",
                },
            ]
        else:
            steps = [
                {
                    "name": "Install dependencies",
                    "run": "pip install setuptools wheel twine build",
                },
                {"name": "Build package", "run": "python -m build"},
                {
                    "name": "Publish package distributions to PyPI",
                    "uses": "pypa/gh-action-pypi-publish@release/v1",
                },
            ]

        steps_yaml = yaml.dump(steps, default_flow_style=False, indent=1)
        steps_yaml = steps_yaml.replace("\n  ", "\n        ")
        steps_yaml = steps_yaml.replace("\n- ", "\n      - ")

        template = self.load_template("pypi_publish.yml")
        rendered = template.format(
            name=name,
            on_section=yaml.dump(on_section, default_flow_style=False, indent=2).rstrip(),
            python_version=python_version,
            other_steps=steps_yaml,
        )

        file_path = os.path.join(self.output_dir, "pypi_publish.yml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(rendered)

        return file_path

    def generate_selected_jobs(self, settings: WorkflowSettings, plan: Plan) -> List[str]:
        """
        Generate a complete set of workflows.

        Args:
            settings: An object containing all workflow generation settings.

        Returns:
            List[str]: List of paths to generated files.
        """
        self._ensure_output_dir()
        generated_files = []

        if settings.include_black:
            file_path = self.generate_black_formatter(branches=settings.branches)
            generated_files.append(file_path)
            if plan is not None:
                plan.mark_done("include_black")

        if settings.include_tests:
            file_path = self.generate_unit_test(
                branches=settings.branches,
                python_versions=settings.python_versions,
                codecov_token=settings.codecov_token,
                coverage=settings.include_codecov,
            )
            generated_files.append(file_path)
            if plan is not None:
                plan.mark_done("include_tests")

        if settings.include_pep8:
            file_path = self.generate_pep8(
                tool=settings.pep8_tool,
                # Use the latest Python version
                python_version=settings.python_versions[-1],
                branches=settings.branches,
            )
            generated_files.append(file_path)
            if plan is not None:
                plan.mark_done("include_pep8")

        if settings.include_autopep8:
            file_path = self.generate_autopep8(branches=settings.branches)
            generated_files.append(file_path)

            if settings.include_fix_pep8:
                file_path = self.generate_fix_pep8_command()
                generated_files.append(file_path)
                if plan is not None:
                    plan.mark_done("include_fix_pep8")
            if plan is not None:
                plan.mark_done("include_autopep8")

        if settings.include_pypi:
            file_path = self.generate_pypi_publish(
                # Use the latest Python version
                python_version=settings.python_versions[-1],
                use_poetry=settings.use_poetry,
            )
            generated_files.append(file_path)
            if plan is not None:
                plan.mark_done("include_pypi")

        return generated_files


class GitLabWorkflowGenerator(WorkflowGenerator):
    def load_template(self, template_name: str) -> str:
        """
        Load a template file content as a string.

        Args:
            template_name: Template file name.

        Returns:
            str: Contents of the template file.
        """
        template_path = os.path.join(
            osa_project_root(),
            "config",
            "templates",
            "workflow",
            "gitlab",
            template_name,
        )
        with open(template_path, "r", encoding="utf-8") as file:
            return file.read()

    def generate_black_formatter(
        self,
        name: str = "Black Formatter",
        python_version: str = "3.10",
        src: str = ".",
        black_options: str = "--check --diff",
        branches: List[str] = None,
    ) -> str:
        branches_section = self._generate_branches_section(branches)

        template = self.load_template("black.yml")
        return template.format(
            python_version=python_version,
            src=src,
            black_options=black_options,
            branches_section=branches_section,
        )

    def generate_unit_test(
        self,
        name: str = "Unit Tests",
        python_versions: List[str] = ["3.9", "3.10"],
        test_dir: str = "tests",
        branches: List[str] = None,
    ) -> str:
        branches_section = self._generate_branches_section(branches)
        matrix_yaml = yaml.dump(
            [{"PYTHON_VERSION": version} for version in python_versions], default_flow_style=False, indent=1
        )
        matrix_yaml = matrix_yaml.replace("\n- ", "\n      - ")

        template = self.load_template("unit_test.yml")
        return template.format(
            matrix_yaml=matrix_yaml,
            test_dir=test_dir,
            branches_section=branches_section,
        )

    def generate_pep8(
        self,
        name: str = "PEP 8 Compliance",
        tool: str = "flake8",
        python_version: str = "3.10",
        src: str = ".",
        branches: List[str] = None,
    ) -> str:
        branches_section = self._generate_branches_section(branches)

        template = self.load_template("pep8.yml")
        return template.format(
            python_version=python_version,
            src=src,
            tool=tool,
            branches_section=branches_section,
        )

    def generate_autopep8(
        self,
        name: str = "AutoPEP8 Format",
        python_version: str = "3.10",
        src: str = ".",
        branches: List[str] = None,
    ) -> str:
        branches_section = self._generate_branches_section(branches)

        template = self.load_template("autopep8.yml")
        return template.format(
            python_version=python_version,
            src=src,
            branches_section=branches_section,
        )

    def generate_fix_pep8_command(
        self,
        name: str = "Fix PEP8 Issues",
        python_version: str = "3.10",
        src: str = ".",
        branches: List[str] = None,
    ) -> str:
        branches_section = self._generate_branches_section(branches)

        template = self.load_template("fix_pep8.yml")
        return template.format(
            python_version=python_version,
            src=src,
            branches_section=branches_section,
        )

    def generate_slash_command_dispatch(
        self,
        name: str = "Slash Command Dispatch",
        commands: List[str] = ["fix-pep8"],
    ) -> str:
        template = self.load_template("slash_command_dispatch.yml")
        return template.format(commands=",".join(commands))

    def generate_pypi_publish(
        self,
        name: str = "PyPI Publish",
        python_version: str = "3.10",
        use_poetry: bool = False,
    ) -> str:
        if use_poetry:
            script = ["pip install poetry", "poetry build", "poetry publish -u $PYPI_USERNAME -p $PYPI_PASSWORD"]
        else:
            script = [
                "pip install twine build",
                "python -m build",
                "twine upload -u $PYPI_USERNAME -p $PYPI_PASSWORD dist/*",
            ]

        script_yaml = yaml.dump(script, default_flow_style=False, indent=1)
        script_yaml = script_yaml.replace("\n- ", "\n    - ")

        template = self.load_template("pypi_publish.yml")
        return template.format(
            python_version=python_version,
            script=script_yaml,
        )

    def _generate_branches_section(self, branches: List[str] = None) -> str:
        if not branches:
            return ""
        return f"only:\n" + "\n".join([f"  - {branch}" for branch in branches])

    def generate_selected_jobs(self, settings: WorkflowSettings, plan: Plan) -> List[str]:
        """
        Generate a complete set of workflows.

        Args:
            settings: An object containing all workflow generation settings.

        Returns:
            List[str]: List of paths to generated files.
        """
        self._ensure_output_dir()
        yaml_parts = []
        generated_files = []

        yaml_parts.append("stages:")
        yaml_parts.append("  - test")
        yaml_parts.append("  - lint")
        yaml_parts.append("  - fix")
        yaml_parts.append("  - deploy")
        yaml_parts.append("")

        if settings.include_black:
            yaml_parts.append(
                self.generate_black_formatter(
                    python_version=settings.python_versions[-1],
                    branches=settings.branches,
                )
            )
            if plan is not None:
                plan.mark_done("include_black")

        if settings.include_tests:
            yaml_parts.append(
                self.generate_unit_test(
                    python_versions=settings.python_versions,
                    branches=settings.branches,
                )
            )
            if plan is not None:
                plan.mark_done("include_tests")

        if settings.include_pep8:
            yaml_parts.append(
                self.generate_pep8(
                    tool=settings.pep8_tool,
                    python_version=settings.python_versions[-1],
                    branches=settings.branches,
                )
            )
            if plan is not None:
                plan.mark_done("include_pep8")

        if settings.include_autopep8:
            yaml_parts.append(
                self.generate_autopep8(
                    python_version=settings.python_versions[-1],
                    branches=settings.branches,
                )
            )

            if settings.include_fix_pep8:
                yaml_parts.append(
                    self.generate_fix_pep8_command(
                        python_version=settings.python_versions[-1],
                        branches=settings.branches,
                    )
                )
                if plan is not None:
                    plan.mark_done("include_fix_pep8")
            if plan is not None:
                plan.mark_done("include_autopep8")

        if settings.include_pypi:
            yaml_parts.append(
                self.generate_pypi_publish(python_version=settings.python_versions[-1], use_poetry=settings.use_poetry)
            )
            if plan is not None:
                plan.mark_done("include_pypi")

        content = "\n".join(part for part in yaml_parts if part) + "\n"
        file_path = os.path.join(self.output_dir, ".gitlab-ci.yml")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        generated_files.append(file_path)
        return generated_files
