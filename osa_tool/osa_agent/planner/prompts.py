def build_parameter_list() -> str:
    """
    Returns a formatted string of all allowed parameters for PlannerNode prompt,
    with their types and logical grouping.
    """
    workflow_params = {
        "generate_workflows": ("flag", "Generate workflows for the repository."),
        "include_tests": ("flag", "Include unit tests workflow."),
        "include_black": ("flag", "Include Black formatter workflow."),
        "include_pep8": ("flag", "Include PEP 8 compliance workflow."),
        "include_autopep8": ("flag", "Include autopep8 formatter workflow."),
        "include_fix_pep8": ("flag", "Include fix-pep8 command workflow."),
        "include_pypi": ("flag", "Include PyPI publish workflow."),
        "python_versions": ("list", "Python versions to test against."),
        "pep8_tool": ("str", "Tool to use for PEP 8 checking (flake8 or pylint)."),
        "use_poetry": ("flag", "Use Poetry for packaging."),
        "branches": ("list", "Branches to trigger the workflows on."),
        "codecov_token": ("flag", "Use Codecov token for uploading coverage."),
        "include_codecov": ("flag", "Include Codecov coverage step in a unit tests workflow."),
    }

    general_params = {
        "about": ("flag", "Generate About section with tags."),
        "community_docs": ("flag", "Generate community-related documentation files, such as Code of Conduct and Contributing guidelines."),
        "convert_notebooks": ("list", "Convert Jupyter notebooks from .ipynb to .py format. Provide paths or leave empty for repo directory."),
        "delete_dir": ("flag", "Enable deleting the downloaded repository after processing."),
        "docstring": ("flag", "Automatically generate docstrings for all Python files in the repository."),
        "ensure_license": ("str", "Enable LICENSE file compilation (bsd-3, mit, ap2)."),
        "readme": ("flag", "Generate a README.md file based on repository content and metadata."),
        "refine_readme": ("flag", "Enable advanced README refinement using a powerful LLM model."),
        "report": ("flag", "Analyze the repository and generate a PDF report with project insights."),
        "translate_dirs": ("flag", "Enable automatic translation of the directory name into English."),
        "translate_readme": ("list", "List of target languages to translate the project's main README into."),
        "organize": ("flag", "Organize the repository structure by adding standard 'tests' and 'examples' directories if missing."),
        "check_doc": ("flag", "Check whether experiments proposed in attached documentation can be reproduced using the selected repository."),
        "check_paper": ("flag", "Check whether experiments proposed in attached research paper can be reproduced using the selected repository."),
    }

    # Combine groups with logical separation
    lines = ["# General repository parameters"]
    for name, (typ, desc) in general_params.items():
        lines.append(f"- {name} ({typ}): {desc}")

    lines.append("\n# Workflow / CI-CD parameters")
    for name, (typ, desc) in workflow_params.items():
        lines.append(f"- {name} ({typ}): {desc}")

    return "\n".join(lines)
