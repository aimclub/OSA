from typing import List


def generate_unit_test_workflow(
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
    Generate a workflow for running unit tests.

    Args:
        name: Name of the workflow
        python_versions: List of Python versions to test against
        os_list: List of operating systems to test on
        dependencies_command: Command to install dependencies
        test_command: Command to run tests
        branches: List of branches to trigger the workflow on
        coverage: Whether to include code coverage reporting
        timeout_minutes: Maximum time in minutes for the job to run
        codecov_token: Whether to use a Codecov token for uploading coverage

    Returns:
        Path to the created workflow file
    """

    # Default to ["push", "pull_request"] unless specific branches are provided
    if branches:
        on_section = {
            "push": {"branches": branches},
            "pull_request": {"branches": branches},
            "workflow_dispatch": {},  # Allow manual triggering
        }
    else:
        on_section = ["push", "pull_request"]

    workflow = {
        "name": name,
        "on": on_section,
        "jobs": {
            "test": {
                "name": "Run Tests",
                "runs-on": "${{ matrix.os }}",
                "timeout-minutes": timeout_minutes,
                "strategy": {
                    "matrix": {"os": os_list, "python-version": python_versions}
                },
                "steps": [
                    {"name": "Checkout repo", "uses": "actions/checkout@v4"},
                    {
                        "name": "Set up Python ${{ matrix.python-version }}",
                        "uses": "actions/setup-python@v4",
                        "with": {"python-version": "${{ matrix.python-version }}"},
                    },
                    {
                        "name": "Install dependencies",
                        "run": dependencies_command
                        + " && pip install pytest pytest-cov",
                    },
                    {"name": "Run tests", "run": test_command + " --cov=."},
                ],
            }
        },
    }

    # Add code coverage if requested
    if coverage:
        codecov_step = {
            "name": "Upload coverage to Codecov",
            "uses": "codecov/codecov-action@v4",
        }

        if codecov_token:
            codecov_step["with"] = {"token": "${{ secrets.CODECOV_TOKEN }}"}

        workflow["jobs"]["test"]["steps"].append(codecov_step)

    return workflow
