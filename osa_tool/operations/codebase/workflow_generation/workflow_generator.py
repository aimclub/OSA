import os
from abc import ABC, abstractmethod
from typing import List, Optional

import yaml

from osa_tool.config.settings import WorkflowSettings
from osa_tool.scheduler.plan import Plan
from osa_tool.utils.utils import osa_project_root


class WorkflowGenerator(ABC):
    """
    Generates CI/CD workflow files for Python projects based on configuration settings.
    
        This class provides methods to create various CI/CD components such as formatters,
        test runners, and publishing jobs, assembling them into complete workflow files.
    
        Attributes:
            output_dir: Directory where generated CI/CD files will be saved.
    
        Methods:
            __init__: Initializes the workflow generator with output directory.
            _ensure_output_dir: Creates output directory if it doesn't exist.
            load_template: Loads template file content as a string.
            generate_black_formatter: Creates black code formatter configuration.
            generate_unit_test: Creates unit testing configuration.
            generate_pep8: Creates PEP8 style checking configuration.
            generate_autopep8: Creates auto-PEP8 fixing configuration.
            generate_fix_pep8_command: Creates command to fix PEP8 issues.
            generate_slash_command_dispatch: Creates slash command dispatch configuration.
            generate_pypi_publish: Creates PyPI publishing configuration.
            generate_selected_jobs: Generates selected CI/CD jobs based on settings.
    """

    def __init__(self, output_dir: str):
        """
        Initialize the CICD files generator.
        
        Args:
            output_dir: Directory where the CICD files will be saved. This path is stored to determine where generated CI/CD configuration files (such as GitHub Actions workflows) will be written.
        
        Why:
            The output directory is essential for organizing and placing the generated CI/CD files in the correct location within the repository, ensuring they are properly integrated and can be executed by the CI/CD system.
        """
        self.output_dir = output_dir

    def _ensure_output_dir(self) -> None:
        """
        Ensure the output directory exists.
        
        This method creates the output directory (and any necessary parent directories)
        if it does not already exist. It uses `exist_ok=True` to avoid raising an error
        if the directory is already present, making the operation idempotent and safe
        for repeated calls.
        
        Args:
            self: The WorkflowGenerator instance.
        
        Returns:
            None
        """
        os.makedirs(self.output_dir, exist_ok=True)

    @abstractmethod
    def load_template(self, template_name: str) -> str:
        """
        Load a template file content as a string.
        
        This is an abstract method that must be implemented by subclasses to define how template files are loaded. It allows the workflow generator to be flexible with different template storage mechanisms (e.g., filesystem, database, embedded resources).
        
        Args:
            template_name: The name of the template file to load.
        
        Returns:
            str: The contents of the template file as a string.
        """
        pass

    @abstractmethod
    def generate_black_formatter(self) -> None:
        """
        Generate the Black code formatter configuration section for the workflow.
        
        This method is responsible for producing the part of the automated workflow that integrates Black, the uncompromising Python code formatter. Including Black ensures consistent code formatting across the project, which improves readability and reduces style-related merge conflicts. The generated content typically specifies the formatter version, options, and the step to run Black on the codebase.
        
        Since this is an abstract method, concrete subclasses must implement it to define the exact configuration and commands appropriate for the target CI/CD platform (e.g., GitHub Actions, GitLab CI).
        """
        pass

    @abstractmethod
    def generate_unit_test(self) -> None:
        """
        Generate the unit test section for the workflow.
        
        This abstract method defines the interface for creating unit test content within the generated workflow documentation. As an abstract method, it must be implemented by subclasses to produce the specific unit test structure, examples, or guidelines appropriate for the project's language and framework. Its purpose is to ensure that all workflow generators include a standardized section dedicated to unit testing, promoting code quality and test coverage as part of the automated documentation process.
        
        Note: This method does not return a value; its implementation should directly output or integrate the unit test content into the broader workflow documentation.
        """
        pass

    @abstractmethod
    def generate_pep8(self) -> None:
        """
        Generate the PEP8 checking part of the workflow.
        
        This abstract method is intended to be implemented by subclasses to produce the necessary configuration or code for enforcing PEP8 style guide compliance within an automated workflow. It ensures that code quality checks for Python style are integrated into the project's continuous integration or development process.
        
        Why: Enforcing PEP8 standards helps maintain consistent, readable, and high-quality Python code across the repository, which is a key aspect of the tool's goal to enhance project maintainability and accessibility.
        """
        pass

    @abstractmethod
    def generate_autopep8(self) -> None:
        """
        Generate the auto-PEP8 code formatting section for the workflow.
        
        This method is responsible for producing the part of the workflow that automatically
        applies PEP 8 style guide corrections to the source code. It ensures code consistency
        and adherence to Python's official style conventions as part of the repository
        enhancement process.
        
        Args:
            None
        
        Returns:
            None
        """
        pass

    @abstractmethod
    def generate_fix_pep8_command(self) -> None:
        """
        Generate the command or code segment for fixing PEP8 style violations in the repository.
        
        This abstract method defines the interface for producing the specific instructions or script
        portion that will address PEP8 compliance issues, such as formatting, naming conventions, and
        line length. It is part of the automated documentation and enhancement pipeline, ensuring
        code style consistency across the project.
        
        Note: This is an abstract method; concrete implementations in subclasses must provide the
        actual command generation logic (e.g., a `black` or `autopep8` command, or a CI/CD step).
        """
        pass

    @abstractmethod
    def generate_slash_command_dispatch(self) -> None:
        """
        Generate the slash command dispatch section for the workflow.
        
        This abstract method defines the interface for creating the part of a workflow
        that handles slash command routing and execution. It is intended to be implemented
        by concrete generators to produce the specific dispatch logic required for
        integrating slash commands into an automated workflow system.
        
        WHY: Slash commands (e.g., '/run', '/docs') are a common interface in chatOps
        or CLI tools to trigger specific actions. This method ensures the generated
        workflow includes a dedicated component to properly receive, parse, and route
        these commands to their corresponding handlers.
        """
        pass

    @abstractmethod
    def generate_pypi_publish(self) -> None:
        """
        Generate the PyPI publishing section for the workflow configuration.
        
        This abstract method defines the structure for creating the continuous integration/deployment
        steps that publish a Python package to the Python Package Index (PyPI). It is intended to be
        implemented by subclasses to produce the specific commands and configuration (such as authentication
        and versioning) required to automate package publication.
        
        WHY: Automating PyPI publication ensures consistent, reliable releases and integrates package
        distribution directly into the CI/CD pipeline, reducing manual errors and streamlining the release process.
        
        Args:
            None
        
        Returns:
            None
        """
        pass

    @abstractmethod
    def generate_selected_jobs(self, settings: WorkflowSettings, plan: Plan) -> List[str]:
        """
        Generate selected jobs based on settings and a given plan.
        
                This abstract method defines the interface for generating CI/CD job files
                (e.g., GitHub Actions workflows) according to the provided settings and
                the execution plan. It allows concrete implementations to create specific
                job configurations tailored to different CI/CD platforms or project needs.
        
                Args:
                    settings: CI/CD specific settings extracted from the config.
                    plan: The execution plan detailing which operations or tasks to include
                          in the generated workflows.
        
                Returns:
                    List[str]: List of file paths to the generated job configuration files.
        """
        pass


class GitHubWorkflowGenerator(WorkflowGenerator):
    """
    Generates GitHub Actions workflows for Python projects.
    
        This class provides methods to create various GitHub Actions workflow files,
        such as those for code formatting, testing, linting, and publishing.
    
        Attributes:
            template_dir: Directory containing workflow template files.
            output_dir: Directory where generated workflow files are saved.
    
        Methods:
            load_template: Loads a template file content as a string.
            generate_black_formatter: Creates a workflow for running the Black code formatter.
            generate_unit_test: Generates a workflow for running unit tests.
            generate_pep8: Generates a workflow for checking PEP 8 compliance.
            generate_autopep8: Generates a workflow for running autopep8 and commenting on pull requests.
            generate_fix_pep8_command: Generates a workflow for fixing PEP8 issues when triggered by a slash command.
            generate_slash_command_dispatch: Generates a workflow for dispatching slash commands.
            generate_pypi_publish: Generates a workflow for publishing to PyPI.
            generate_selected_jobs: Generates a complete set of workflows.
    """

    def load_template(self, template_name: str) -> str:
        """
        Load a template file content as a string.
        
        The method constructs the full filesystem path to a specific template file located within the project's template directory structure and reads its contents. This is used to retrieve predefined workflow templates for generating GitHub Actions configurations.
        
        Args:
            template_name: The name of the template file (including extension) located in the project's 'config/templates/workflow/github_gitverse/' directory.
        
        Returns:
            str: The UTF-8 decoded contents of the template file as a string.
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
        Create a GitHub Actions workflow for running the Black code formatter using the official Black action.
        
        The workflow is triggered on push and pull request events. If no branches are specified, it triggers on all branches. The generated workflow file is saved in the output directory.
        
        Args:
            name: Workflow name (default: "Black Formatter").
            job_name: Job name inside the workflow (default: "Lint").
            branches: List of branches to trigger on. If empty, triggers on all branches (default: []).
            black_options: Options to pass to Black formatter (default: "--check --diff").
            src: Source directory to format (default: ".").
            use_pyproject: Whether to use pyproject.toml configuration. If True, a Python setup step is added and the Black action is configured to use pyproject.toml (default: False).
            version: Specific Black version to use. If provided, pins the Black action to this version.
            jupyter: Whether to format Jupyter notebooks (default: False).
            python_version: Python version to setup. Required if use_pyproject is True; otherwise defaults to "3.11" when a Python setup step is added.
        
        Returns:
            str: Path to the generated workflow file (e.g., "output_dir/black.yml").
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
        
        The workflow is configured to run on specified branches (or all branches if none are provided) and includes steps for installing dependencies, executing tests, and optionally uploading coverage reports to Codecov. This automation ensures consistent testing across multiple Python versions and operating systems.
        
        Args:
            name: Name of the workflow as it will appear in GitHub Actions.
            python_versions: List of Python versions to test against. Defaults to ["3.9", "3.10"].
            os_list: List of operating systems to test on. Defaults to ["ubuntu-latest"].
            dependencies_command: Command to install dependencies before running tests.
            test_command: Command to execute the unit tests.
            branches: List of branches that trigger the workflow on push or pull request events. If empty, the workflow triggers on all branches.
            coverage: Whether to include code coverage reporting. If True, a coverage upload step is added.
            timeout_minutes: Maximum time in minutes for the job to run before being cancelled.
            codecov_token: Whether to use a Codecov token for uploading coverage. Requires a secret named CODECOV_TOKEN in the repository settings if enabled.
        
        Returns:
            str: Path to the generated YAML file (unit_test.yml) within the output directory.
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
        
        This method creates a GitHub Actions workflow file (pep8.yml) that runs a specified linter on code pushes and pull requests. It is used to automate code style enforcement in a repository.
        
        Args:
            name: Name of the workflow as it will appear in GitHub Actions.
            tool: Tool to use for PEP 8 checking (flake8 or pylint). The method validates this choice.
            python_version: Python version to use in the workflow environment.
            args: Additional command-line arguments to pass to the tool. If empty, only the tool command is used.
            branches: List of branches to trigger the workflow on. If provided, triggers are limited to these branches; otherwise, the workflow runs on all branches for push and pull_request events.
        
        Returns:
            str: Path to the generated workflow file (pep8.yml) within the output directory.
        
        Raises:
            ValueError: If the `tool` argument is not 'flake8' or 'pylint'.
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
        
        This method creates a GitHub Actions workflow file that automatically formats Python code using autopep8 when a pull request is opened or updated. The formatted changes are then committed back and, if configured, a comment is posted on the pull request. This ensures consistent code style across the repository without manual intervention.
        
        Args:
            name: Name of the workflow as displayed in GitHub Actions.
            max_line_length: Maximum line length for autopep8 to enforce.
            aggressive_level: Aggressive level for autopep8 (1 or 2). Level 1 performs basic formatting fixes, while level 2 includes more aggressive changes (e.g., line re‑wrapping). Must be 1 or 2.
            branches: List of branch names to trigger the workflow on pull requests. If empty, the workflow triggers on pull requests to any branch.
        
        Returns:
            str: Path to the generated workflow file (autopep8.yml) within the output directory.
        
        Raises:
            ValueError: If aggressive_level is not 1 or 2.
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
        
        The workflow is written to a YAML file in the output directory. It uses autopep8 to automatically format Python code according to PEP8 standards, with configurable line length and aggressiveness. The workflow can be triggered via a slash command (e.g., `/fix-pep8`) in the repository.
        
        Args:
            name: Name of the workflow.
            max_line_length: Maximum line length for autopep8.
            aggressive_level: Aggressive level for autopep8 (1 or 2). Level 1 performs basic fixes; level 2 includes more aggressive changes.
            repo_access_token: Whether to use a repository access token. If True, uses a secret named REPO_ACCESS_TOKEN; otherwise, uses the default GitHub token.
        
        Returns:
            str: Path to the generated YAML file.
        
        Raises:
            ValueError: If aggressive_level is not 1 or 2.
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
        
        This method creates a GitHub Actions workflow file that responds to slash commands (e.g., "/fix-pep8") in pull request comments. The workflow is designed to trigger automated tasks or bots when specific commands are issued, facilitating repository automation.
        
        Args:
            name: Name of the workflow as it will appear in GitHub Actions.
            commands: List of slash command strings (without the leading slash) that the workflow will listen for and dispatch.
            permission: Permission level for the workflow, controlling the GitHub token's scope (e.g., "none", "read", "write").
        
        Returns:
            str: Path to the generated YAML file (slash_command_dispatch.yml) within the output directory.
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
        Generate a GitHub Actions workflow for publishing a Python package to PyPI.
        
        The workflow is written to a YAML file in the output directory. It supports two packaging methods (standard `build`/`twine` or Poetry) and configurable triggers (tags, releases, or manual dispatch). The method ensures at least one automatic trigger is enabled to prevent workflows that never run.
        
        Args:
            name: Display name for the workflow in the GitHub Actions UI.
            python_version: Version of Python to set up in the runner environment.
            use_poetry: If True, uses Poetry for dependency management and building. If False, uses setuptools/wheel/twine with `python -m build`.
            trigger_on_tags: If True, the workflow triggers automatically on pushes to version tags matching '*.*.*' (e.g., v1.2.3).
            trigger_on_release: If True, the workflow triggers automatically when a new GitHub release is created.
            manual_trigger: If True, adds a `workflow_dispatch` event, allowing the workflow to be triggered manually from the GitHub UI.
        
        Returns:
            str: The filesystem path to the generated workflow YAML file.
        
        Raises:
            ValueError: If both `trigger_on_tags` and `trigger_on_release` are False, because a workflow must have at least one automatic trigger to be useful.
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
        Generate a complete set of workflows based on the provided settings and plan.
        
        This method conditionally creates individual workflow configuration files (e.g., for code formatting, testing, linting, and publishing) according to the flags enabled in the settings. Each generated file corresponds to a specific job (like Black, unit tests, PEP8 checks, etc.). If a plan object is provided, it is updated to mark each completed task, enabling progress tracking within a larger enhancement pipeline.
        
        Args:
            settings: An object containing all workflow generation settings (e.g., flags for including Black, tests, PEP8, etc., along with associated configuration like branches and Python versions).
            plan: An optional plan object for tracking task completion. If provided, tasks are marked as done as each corresponding workflow is generated.
        
        Returns:
            List[str]: List of file paths to the generated workflow configuration files.
        
        Why:
            The method orchestrates the generation of multiple, independent CI/CD workflows by delegating to specific generator methods. It ensures the output directory exists before writing any files and aggregates the results. The optional plan tracking allows the caller to monitor which parts of a multi-step documentation/enhancement process have been completed.
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
    """
    Generates GitLab CI/CD pipeline configurations for various development workflows.
    
        Methods:
            load_template: Load a template file content as a string.
            generate_black_formatter: Generates a YAML configuration for a Black code formatter job in a GitLab CI/CD pipeline.
            generate_unit_test: Generates a YAML configuration for unit test workflows.
            generate_pep8: Generates a PEP 8 compliance workflow configuration.
            generate_autopep8: Generates a GitLab CI/CD workflow configuration for AutoPEP8 code formatting.
            generate_fix_pep8_command: Generates a GitLab CI/CD pipeline command for fixing PEP8 style issues.
            generate_slash_command_dispatch: Generates a YAML dispatch workflow for slash commands.
            generate_pypi_publish: Generates a GitHub Actions workflow YAML for publishing a Python package to PyPI.
            _generate_branches_section: Generates a section of text listing branches.
            generate_selected_jobs: Generate a complete set of workflows.
    
        Attributes:
            template_dir: The directory path where template files are stored.
            output_dir: The directory path where generated YAML files will be saved.
    
        These methods create YAML configurations for specific CI/CD jobs like code formatting, testing, and publishing. The attributes define the file system locations used for reading templates and writing the final pipeline configurations.
    """

    def load_template(self, template_name: str) -> str:
        """
        Load a template file content as a string.
        
        The method constructs the full path to a template file by joining the project root directory with a fixed subdirectory structure specific to GitLab workflow templates. This ensures templates are reliably located relative to the project's installation, regardless of the current working directory.
        
        Args:
            template_name: Template file name (e.g., "pipeline.yml").
        
        Returns:
            str: Contents of the template file, read with UTF-8 encoding.
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
        """
        Generates a YAML configuration for a Black code formatter job in a GitLab CI/CD pipeline.
        
        Args:
            name: The name of the job in the pipeline. This parameter is accepted for interface consistency but is not directly used in the generated YAML.
            python_version: The Python version to use for the job environment.
            src: The source directory or file path to format.
            black_options: Command-line options to pass to the Black formatter.
            branches: A list of branch names where this job should run. If None, the branch restriction is omitted from the configuration.
        
        Returns:
            str: The complete YAML configuration string for the Black formatter job.
        
        Why:
            The method loads a predefined YAML template ("black.yml") and populates it with the provided parameters. The branch list is processed into a formatted "only:" section (or omitted if not specified), allowing the job to be conditionally restricted to specific branches in the pipeline.
        """
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
        """
        Generates a YAML configuration for unit test workflows in GitLab CI/CD.
        
        Args:
            name: The name of the workflow.
            python_versions: A list of Python versions to test against. Defaults to ["3.9", "3.10"].
            test_dir: The directory containing the test files. Defaults to "tests".
            branches: A list of branches to run the workflow on. If None or empty, the branch restriction is omitted from the generated configuration.
        
        Returns:
            A string containing the generated YAML configuration.
        
        Why:
            This method creates a GitLab CI/CD pipeline configuration specifically for running unit tests across multiple Python versions. It uses a template ("unit_test.yml") to ensure a consistent structure, while dynamically injecting the Python version matrix, test directory, and optional branch restrictions. The branch restriction is conditionally included to allow pipelines to run on all branches or be limited to specific ones.
        """
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
        """
        Generates a PEP 8 compliance workflow configuration for GitLab CI/CD.
        
        Args:
            name: The name of the workflow.
            tool: The linter tool to use for checking compliance.
            python_version: The Python version to use in the workflow.
            src: The source directory to check.
            branches: A list of branches to run the workflow on. If None or empty, the workflow will not be restricted to specific branches.
        
        Returns:
            A string containing the generated workflow configuration.
        
        Why:
            This method creates a ready-to-use GitLab CI configuration that enforces PEP 8 style checking on specified branches. It uses a template file to ensure the output follows GitLab CI syntax and integrates a helper to conditionally include branch restrictions, providing a flexible and reusable way to add standardized code quality checks to a repository.
        """
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
        """
        Generates a GitLab CI/CD workflow configuration for AutoPEP8 code formatting.
        The configuration ensures code is automatically formatted according to PEP 8 standards as part of the CI pipeline.
        
        Args:
            name: The name of the CI/CD job.
            python_version: The Python version to use for the job environment.
            src: The source directory to be formatted.
            branches: A list of branch names to run the job on. If None or empty, the branch restriction is omitted from the configuration.
        
        Returns:
            str: The complete GitLab CI/CD YAML configuration for the AutoPEP8 job, generated by populating a dedicated template with the provided parameters.
        """
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
        """
        Generates a GitLab CI/CD pipeline command for fixing PEP8 style issues.
        
        This method creates a YAML configuration for a GitLab CI job that automatically corrects PEP8 violations in the source code. It is typically used to enforce and maintain consistent Python code style across a project as part of an automated workflow.
        
        Args:
            name: The name of the pipeline job.
            python_version: The Python version to use in the CI environment.
            src: The source directory to check for PEP8 issues.
            branches: A list of branch names to run the pipeline on. If None or empty, the branch restriction is omitted from the generated configuration.
        
        Returns:
            str: The formatted YAML content for the GitLab CI/CD pipeline job.
        """
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
        """
        Generates a YAML dispatch workflow for slash commands.
        
        The workflow is built from a predefined template, which is populated with the provided command list. This allows for automated triggering of specific actions (like "fix-pep8") via slash commands in GitLab merge request comments.
        
        Args:
            name: The name of the generated workflow.
            commands: A list of slash command names to include in the workflow. The list is joined into a comma-separated string for template insertion.
        
        Returns:
            str: The formatted YAML content for the slash command dispatch workflow.
        """
        template = self.load_template("slash_command_dispatch.yml")
        return template.format(commands=",".join(commands))

    def generate_pypi_publish(
        self,
        name: str = "PyPI Publish",
        python_version: str = "3.10",
        use_poetry: bool = False,
    ) -> str:
        """
        Generates a GitHub Actions workflow YAML for publishing a Python package to PyPI.
        
        The workflow is built from a template file, which is populated with the provided parameters and a generated script block. The script block contains the commands for building and publishing the package, differing based on whether Poetry or twine/build is used.
        
        Args:
            name: The name of the workflow job.
            python_version: The version of Python to use in the workflow.
            use_poetry: If True, uses Poetry for building and publishing. If False, uses twine and build.
        
        Returns:
            str: The formatted YAML content for the PyPI publish workflow.
        """
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

    @staticmethod
    def _generate_branches_section(branches: List[str] = None) -> str:
        """
        Generates a section of text listing branches for a GitLab CI/CD configuration.
        
        Args:
            branches: A list of branch names. If None or empty, the method returns an empty string.
        
        Returns:
            A formatted string listing the branches under an "only:" key, with each branch indented and prefixed with a dash, suitable for inclusion in a GitLab CI/CD configuration file. Returns an empty string if no branches are provided, allowing the section to be omitted when not needed.
        
        Why:
            This method is used to dynamically generate the "only" clause in a GitLab CI configuration, which restricts pipeline execution to specific branches. By returning an empty string when no branches are given, it provides flexibility to conditionally include or exclude this restriction.
        """
        if not branches:
            return ""
        return f"only:\n" + "\n".join([f"  - {branch}" for branch in branches])

    def generate_selected_jobs(self, settings: WorkflowSettings, plan: Plan) -> List[str]:
        """
        Generate a complete GitLab CI/CD workflow configuration file (.gitlab-ci.yml) based on selected job settings.
        
        This method constructs a pipeline by conditionally including stages for code formatting, testing, linting, fixing, and deployment, according to the provided settings. It writes the final YAML content to a file and returns its path.
        
        Args:
            settings: An object containing all workflow generation settings, such as which jobs to include (e.g., include_black, include_tests) and their parameters (e.g., python_versions, branches).
            plan: An optional Plan object for tracking task completion. If provided, the method marks each included job as done in the plan after generating its configuration.
        
        Returns:
            List[str]: A list containing the single file path to the generated .gitlab-ci.yml file.
        
        Why:
            The method centralizes the generation of a GitLab CI pipeline by orchestrating multiple specialized job generators. It ensures the output directory exists, builds the YAML content incrementally, and optionally updates a progress plan. This allows for a configurable, modular pipeline creation where users can select only the CI/CD jobs they need.
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
