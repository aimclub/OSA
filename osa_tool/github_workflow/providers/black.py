from typing import List


from typing import List, Optional


def generate_black_formatter_workflow(
    name: str = "Black Formatter",
    job_name: str = "Lint",
    branches: Optional[List[str]] = None,
    black_options: str = "--check --diff",
    src: str = ".",
    use_pyproject: bool = False,
    version: Optional[str] = None,
    jupyter: bool = False,
    python_version: Optional[str] = None,  # E.g., "3.11" or "3.13"
) -> dict:
    """
    Generate a GitHub Actions workflow for running the Black code formatter using the official Black action.

    Parameters:
    - name (str): Name of the workflow (default: "Black Formatter").
    - job_name (str): Name of the job within the workflow (default: "Lint").
    - branches (Optional[List[str]]): List of branches to trigger the workflow on (default: None, triggers on all pushes and pull requests).
    - black_options (str): Options to pass to the Black formatter (default: "--check --diff").
    - src (str): Source directory to format (default: "." for the entire repository).
    - use_pyproject (bool): Whether to use the configuration from pyproject.toml (default: False).
    - version (Optional[str]): Specific version of Black to use (default: None, uses the latest stable version).
    - jupyter (bool): Whether to format Jupyter notebooks (default: False).
    - python_version (Optional[str]): Python version to set up (default: None, uses Python 3.11 if not specified).

    Returns:
    - dict: A dictionary representing the GitHub Actions workflow configuration.
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

    # Default to ["push", "pull_request"] unless specific branches are provided
    if branches:
        on_section = {
            "push": {"branches": branches},
            "pull_request": {"branches": branches},
        }
    else:
        on_section = ["push", "pull_request"]

    workflow = {
        "name": name,
        "on": on_section,
        "jobs": {"lint": {"name": job_name, "runs-on": "ubuntu-latest", "steps": steps}},
    }
    return workflow
