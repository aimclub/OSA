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
    """
    TestWorkflowGeneration
    
    This unittest.TestCase class verifies that workflow generation functions produce
    correct YAML files for the Black formatter and unit test workflows. It creates a
    temporary directory in setUp, generates the workflows, writes them to disk, and
    ensures the resulting files exist and match expected paths.
    
    Class Methods:
    - setUp
    - tearDown
    - test_generate_black_workflow
    - test_generate_unit_test_workflow
    
    Attributes:
    - temp_dir (created in setUp)
    - generator (instance used to write workflows)
    """

    def setUp(self):
        """Create a temporary directory for generated workflows."""
        self.temp_dir = tempfile.mkdtemp()
        self.generator = GitHubWorkflowGenerator(output_dir=self.temp_dir)

    def tearDown(self):
        """Remove the temporary directory."""
        shutil.rmtree(self.temp_dir)

    def test_generate_black_workflow(self):
        """
        Test that the Black formatter workflow is correctly generated and written to disk.
        
        Parameters
        ----------
        self : object
            The test case instance.
        
        This test calls :func:`generate_black_formatter_workflow` to obtain a workflow dictionary, writes it to a file named ``black.yml`` using the generator's internal
        ``_write_workflow`` method, and then verifies that the returned path matches the expected path in the temporary directory. It also checks that the file was actually created.
        
        Returns
        -------
        None
            The method performs assertions and does not return a value.
        """
        expected_path = Path(self.temp_dir) / "black.yml"
        black_workflow = generate_black_formatter_workflow()
        generated_path = self.generator._write_workflow("black.yml", black_workflow)
        self.assertEqual(generated_path, str(expected_path))
        self.assertTrue(expected_path.exists())

    def test_generate_unit_test_workflow(self):
        """
        Test the generation of the unit test workflow.
        
        This test verifies that the `generate_unit_test_workflow` function produces a workflow
        definition that is correctly written to the expected file path. It compares the
        generated path returned by the generator with the expected path and ensures that
        the file is created on disk.
        
        Args:
            self: The test case instance.
        
        Returns:
            None
        """
        expected_path = Path(self.temp_dir) / "unit-tests.yml"
        unit_test_workflow = generate_unit_test_workflow()
        generated_path = self.generator._write_workflow("unit-tests.yml", unit_test_workflow)
        self.assertEqual(generated_path, str(expected_path))
        self.assertTrue(expected_path.exists())


if __name__ == "__main__":
    unittest.main()
