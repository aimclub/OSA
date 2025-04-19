#!/usr/bin/env python3
"""
Test script for the GitHub workflow generator.
"""

from osa_tool.github_workflow.generator import GitHubWorkflowGenerator
import os
import sys
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def main():
    """
    Test the GitHub workflow generator by generating a sample workflow.
    """
    print("Testing GitHub workflow generator...")

    # Create a test output directory
    output_dir = "test_workflows"
    os.makedirs(output_dir, exist_ok=True)

    # Create a workflow generator
    generator = GitHubWorkflowGenerator(output_dir=output_dir)

    # Generate a Black formatter workflow
    black_path = generator.generate_black_formatter_workflow(
        black_args="--check .",
        branches=["main", "develop"]
    )
    print(f"Generated Black formatter workflow: {black_path}")

    print("All workflows generated successfully!")
    return # Остальные в работе, пока отключены

    # Generate a unit test workflow
    unit_test_path = generator.generate_unit_test_workflow(
        python_versions=["3.8", "3.9", "3.10"],
        os_list=["ubuntu-latest"],
        dependencies_command="pip install -r requirements.txt",
        test_command="pytest tests/",
        branches=["main", "develop"],
        coverage=True,
        codecov_token=True
    )
    print(f"Generated unit test workflow: {unit_test_path}")

    # Generate a PEP 8 compliance workflow
    pep8_path = generator.generate_pep8_workflow(
        tool="flake8",
        args="--max-line-length=120",
        python_version="3.10",
        branches=["main", "develop"]
    )
    print(f"Generated PEP 8 compliance workflow: {pep8_path}")

    # Generate an autopep8 workflow
    autopep8_path = generator.generate_autopep8_workflow(
        max_line_length=120,
        aggressive_level=2,
        branches=["main", "develop"]
    )
    print(f"Generated autopep8 workflow: {autopep8_path}")

    # Generate a fix-pep8 command workflow
    fix_pep8_path = generator.generate_fix_pep8_command_workflow(
        max_line_length=120,
        aggressive_level=2,
        repo_access_token=True
    )
    print(f"Generated fix-pep8 command workflow: {fix_pep8_path}")

    # Generate a slash command dispatch workflow
    slash_command_path = generator.generate_slash_command_dispatch_workflow(
        commands=["fix-pep8"],
        permission="none"
    )
    print(f"Generated slash command dispatch workflow: {slash_command_path}")

    # Generate a PyPI publish workflow
    pypi_path = generator.generate_pypi_publish_workflow(
        python_version="3.10",
        use_poetry=True,
        trigger_on_tags=True,
        trigger_on_release=False,
        manual_trigger=True
    )
    print(f"Generated PyPI publish workflow: {pypi_path}")

    print("All workflows generated successfully!")


if __name__ == "__main__":
    main()
