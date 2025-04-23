import os
from typing import List

from osa_tool.analytics.report_maker import ReportGenerator
from osa_tool.analytics.sourcerank import SourceRank
from osa_tool.arguments_parser import get_cli_args
from osa_tool.config.settings import ConfigLoader, GitSettings
from osa_tool.convertion.notebook_converter import NotebookConverter
from osa_tool.github_agent.github_agent import GithubAgent
from osa_tool.github_workflow import generate_workflows_from_settings
from osa_tool.osatreesitter.docgen import DocGen
from osa_tool.osatreesitter.osa_treesitter import OSA_TreeSitter
from osa_tool.readmegen.readme_core import readme_agent
from osa_tool.translation.dir_translator import DirectoryTranslator
from osa_tool.utils import (
    delete_repository,
    logger,
    parse_folder_name
)


def main():
    """Main function to generate a README.md file for a GitHub repository.

    Handles command-line arguments, clones the repository, creates and checks out a branch,
    generates the README.md file, and commits and pushes the changes.
    """

    # Create a command line argument parser
    args = get_cli_args()
    repo_url = args.repository
    api = args.api
    base_url = args.base_url
    model_name = args.model
    article = args.article
    notebook_paths = args.convert_notebooks

    # Extract workflow-related arguments
    generate_workflows = args.generate_workflows
    workflows_output_dir = args.workflows_output_dir
    include_tests = args.include_tests
    include_black = args.include_black
    include_pep8 = args.include_pep8
    include_autopep8 = args.include_autopep8
    include_fix_pep8 = args.include_fix_pep8
    include_pypi = args.include_pypi
    python_versions = args.python_versions
    pep8_tool = args.pep8_tool
    use_poetry = args.use_poetry
    branches = args.branches
    codecov_token = args.codecov_token
    include_codecov = args.include_codecov

    try:
        # Load configurations and update
        config = load_configuration(
            repo_url=repo_url,
            api=api,
            base_url=base_url,
            model_name=model_name,
            generate_workflows=generate_workflows,
            workflows_output_dir=workflows_output_dir,
            include_tests=include_tests,
            include_black=include_black,
            include_pep8=include_pep8,
            include_autopep8=include_autopep8,
            include_fix_pep8=include_fix_pep8,
            include_pypi=include_pypi,
            python_versions=python_versions,
            pep8_tool=pep8_tool,
            use_poetry=use_poetry,
            branches=branches,
            codecov_token=codecov_token,
            include_codecov=include_codecov
        )

        # Initialize GitHub agent and perform operations
        github_agent = GithubAgent(repo_url)
        github_agent.star_repository()
        github_agent.create_fork()
        github_agent.clone_repository()
        github_agent.create_and_checkout_branch()

        # .ipynb to .py convertion
        if notebook_paths is not None:
            convert_notebooks(repo_url, notebook_paths)

        # Repository Analysis Report generation
        sourcerank = SourceRank(config)
        analytics = ReportGenerator(config, sourcerank)
        analytics.build_pdf()

        # Auto translating names of directories
        if args.translate_dirs:
            translation = DirectoryTranslator(config)
            translation.rename_directories_and_files()

        # Docstring generation
        generate_docstrings(config)

        # License compiling
        if not sourcerank.license_presence():
            compile_license_file(sourcerank)

        # Readme generation
        readme_agent(config, article)

        # Generate GitHub workflows
        if generate_workflows:
            generate_github_workflows(config)
        
        github_agent.commit_and_push_changes()
        github_agent.create_pull_request()

        if args.delete_dir:
            delete_repository(repo_url)

        logger.info("All operations completed successfully.")
    except Exception as e:
        logger.error("Error: %s", e, exc_info=True)


def convert_notebooks(repo_url: str, notebook_paths: List[str] | None = None) -> None:
    """Converts Jupyter notebooks to Python scripts based on provided paths.

    Args:
        repo_url: Repository url.
        notebook_paths: A list of paths to the notebooks to be converted (or None).
                        If empty, the converter will process the current repository.
    """
    try:
        converter = NotebookConverter()
        if len(notebook_paths) == 0:
            converter.process_path(os.path.basename(repo_url))
        else:
            for path in notebook_paths:
                converter.process_path(path)

    except Exception as e:
        logger.error("Error while converting notebooks: %s", repr(e), exc_info=True)


def compile_license_file(sourcerank: SourceRank):
    """
    Compiles a license file for a software project using a specified template.

    This method takes a SourceRank object as input, extracts necessary information such as creation year and author
    to compile a license file based on a predefined template. The compiled license file is then saved in the repository
    directory of the SourceRank object.

    Parameters:
        - sourcerank: SourceRank object containing metadata about the software project.

    Returns:
        None. The compiled license file is saved in the repository directory of the SourceRank object.
    """
    try:
        logger.info("LICENSE was not resolved, compiling started...")
        license_template_path = os.path.join(
            os.getcwd(), "osa_tool", "docs", "license_template", "licenses.toml"
        )
        license_template = FileHandler().read_toml(license_template_path)
        license_type = "bsd"
        year = sourcerank.metadata.created_at[:4]
        author = sourcerank.metadata.owner
        license_text = license_template[license_type]["template"].format(
            year=year, author=author
        )
        license_output_path = os.path.join(sourcerank.repo_path, "LICENSE")
        with open(license_output_path, "w") as f:
            f.write(license_text)
        logger.info(
            f"""LICENSE has been successfully compiled at {os.path.join(sourcerank.repo_path, "LICENSE")}"""
        )
    except Exception as e:
        logger.error("Error while compiling LICENSE: %s", e, exc_info=True)


def generate_docstrings(config_loader: ConfigLoader) -> None:
    """Generates a docstrings for .py's classes and methods of the provided repository.

    Args:
        config_loader: The configuration object which contains settings for osa_tool.

    """
    try:
        repo_url = config_loader.config.git.repository
        ts = OSA_TreeSitter(parse_folder_name(repo_url))
        res = ts.analyze_directory(ts.cwd)
        dg = DocGen(config_loader)
        dg.process_python_file(res)

    except Exception as e:
        logger.error("Error while docstring generation: %s", repr(e), exc_info=True)


def load_configuration(
        repo_url: str,
        api: str,
        base_url: str,
        model_name: str,
        workflows_output_dir: str,
        generate_workflows: bool,
        include_tests: bool,
        include_black: bool,
        include_pep8: bool,
        include_autopep8: bool,
        include_fix_pep8: bool,
        include_pypi: bool,
        python_versions: List[str],
        pep8_tool: str,
        use_poetry: bool,
        branches: List[str],
        codecov_token: str,
        include_codecov: bool,
) -> ConfigLoader:
    """
    Loads configuration for osa_tool.

    Args:
        repo_url: URL of the GitHub repository.
        api: LLM API service provider.
        base_url: URL of the provider compatible with API OpenAI
        model_name: Specific LLM model to use.
        workflows_output_dir: Directory where GitHub workflows will be generated.        
        generate_workflows: Flag to generate GitHub workflows (True/False).
        include_tests: Whether to include tests in the workflows.
        include_black: Whether to include black formatting in the workflows.
        include_pep8: Whether to include pep8 in the workflows.
        include_autopep8: Whether to include autopep8 in the workflows.
        include_fix_pep8: Whether to include pep8 fixing in the workflows.
        include_pypi: Whether to include pypi deployment in the workflows.
        python_versions: List of Python versions to include in the workflows.
        pep8_tool: Tool to use for pep8 checking.
        use_poetry: Whether to use Poetry for dependency management.
        branches: List of branches to include in the workflows.
        codecov_token: Codecov token for code coverage.

    Returns:
        config_loader: The configuration object which contains settings for osa_tool.
    """
    config_loader = ConfigLoader()

    config_loader.config.git = GitSettings(repository=repo_url)
    config_loader.config.llm = config_loader.config.llm.model_copy(
        update={"api": api, "url": base_url, "model": model_name}
    )
    config_loader.config.workflows = config_loader.config.workflows.model_copy(update={
        "generate_workflows": generate_workflows,
        "output_dir": workflows_output_dir,
        "include_tests": include_tests,
        "include_black": include_black,
        "include_pep8": include_pep8,
        "include_autopep8": include_autopep8,
        "include_fix_pep8": include_fix_pep8,
        "include_pypi": include_pypi,
        "python_versions": python_versions,
        "pep8_tool": pep8_tool,
        "use_poetry": use_poetry,
        "branches": branches,
        "codecov_token": codecov_token,
        "include_codecov": include_codecov
    })
    logger.info("Config successfully updated and loaded")
    return config_loader


def generate_github_workflows(config_loader: ConfigLoader) -> None:
    """
    Generate GitHub Action workflows based on configuration settings.
    Args:
        config: Configuration loader object which contains workflow settings
    """
    try:
        logger.info("Generating GitHub action workflows...")

        # Get the workflow settings from the config
        workflow_settings = config_loader.config.workflows
        repo_url = config_loader.config.git.repository
        output_dir = os.path.join(os.getcwd(), parse_folder_name(
            repo_url), workflow_settings.output_dir)

        created_files = generate_workflows_from_settings(
            workflow_settings, output_dir)

        if created_files:
            formatted_files = "\n".join(f" - {file}" for file in created_files)
            logger.info("Successfully generated the following workflow files:\n%s", formatted_files)
        else:
            logger.info("No workflow files were generated.")

    except Exception as e:
        logger.error("Error while generating GitHub workflows: %s",
                     repr(e), exc_info=True)


if __name__ == "__main__":
    main()
