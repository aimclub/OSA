"""
Integration tests for the GitHub workflow generator.  These tests verify that
workflow files are generated correctly.
"""

import shutil
import tempfile
import unittest
from pathlib import Path

from osa_tool.github_workflow.generator import GitHubWorkflowGenerator
from osa_tool.github_workflow.providers.black import generate_black_formatter_workflow
from osa_tool.github_workflow.providers.unit_test import generate_unit_test_workflow


class TestWorkflowGeneration(unittest.TestCase):

    def setUp(self):
        """Create a temporary directory for generated workflows."""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = GitHubWorkflowGenerator(output_dir=self.temp_dir)

    def tearDown(self):
        """Remove the temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_generate_black_workflow(self):
        expected_path = Path(self.temp_dir) / "black.yml"
        black_workflow = generate_black_formatter_workflow()
        generated_path = self.generator._write_workflow("black.yml", black_workflow)
        self.assertEqual(generated_path, str(expected_path))
        self.assertTrue(expected_path.exists())

    def test_generate_unit_test_workflow(self):
        expected_path = Path(self.temp_dir) / "unit-tests.yml"
        unit_test_workflow = generate_unit_test_workflow()
        generated_path = self.generator._write_workflow("unit-tests.yml", unit_test_workflow)
        self.assertEqual(generated_path, str(expected_path))
        self.assertTrue(expected_path.exists())


if __name__ == "__main__":
    unittest.main()
