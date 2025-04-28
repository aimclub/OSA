"""
GitHub Workflow Generator module for creating CI/CD pipelines for Python repositories.

This module provides tools to generate GitHub Action workflows for:
- Automated unit test execution
- Automated code formatting using Black
- Automated PEP 8 compliance checks
- PyPI publication
- Advanced autopep8 formatting with PR comments
- Slash command for fixing PEP8 issues
"""

from .generator import (
    GitHubWorkflowGenerator,
    generate_workflows_from_settings
)

__all__ = [
    'GitHubWorkflowGenerator',
    'generate_workflows_from_settings'
]