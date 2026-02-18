import unittest
from osa_tool.github_workflow.providers.unit_test import generate_unit_test_workflow


class TestUnitTestWorkflowGenerator(unittest.TestCase):
    """
    TestUnitTestWorkflowGenerator
    
    This test class verifies the correctness of the unit test workflow generation
    functionality provided by the workflow generator. It contains unit tests that
    check the default configuration, custom configuration, and inclusion of a
    Codecov token in the generated workflow.
    
    Class Methods:
    - test_generate_unit_test_workflow_default:
    """

    def test_generate_unit_test_workflow_default(self):
        """
        Test default unit test workflow generation.
        
        This test verifies that the workflow produced by `generate_unit_test_workflow()` contains the expected default
        configuration. It checks the workflow name, trigger events, job name, operating system and Python version matrix,
        checkout and setup steps, test installation and execution commands, and the inclusion of the Codecov action
        without a token.
        
        Args:
            self: The test case instance.
        
        Returns:
            None
        """
        workflow = generate_unit_test_workflow()

        self.assertEqual(workflow["name"], "Unit Tests")
        self.assertEqual(workflow["on"], ["push", "pull_request"])
        self.assertEqual(workflow["jobs"]["test"]["name"], "Run Tests")
        self.assertEqual(workflow["jobs"]["test"]["strategy"]["matrix"]["os"], ["ubuntu-latest"])
        self.assertEqual(
            workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"],
            ["3.9", "3.10"],
        )
        self.assertEqual(workflow["jobs"]["test"]["steps"][0]["uses"], "actions/checkout@v4")
        self.assertEqual(workflow["jobs"]["test"]["steps"][1]["uses"], "actions/setup-python@v4")
        self.assertEqual(
            workflow["jobs"]["test"]["steps"][2]["run"],
            "pip install -r requirements.txt && pip install pytest pytest-cov",
        )
        self.assertEqual(workflow["jobs"]["test"]["steps"][3]["run"], "pytest tests/ --cov=.")
        self.assertEqual(
            workflow["jobs"]["test"]["steps"][4]["uses"], "codecov/codecov-action@v4"
        )  # Default includes Codecov
        self.assertNotIn("token", workflow["jobs"]["test"]["steps"][4].get("with", {}))  # No token by default

    def test_generate_unit_test_workflow_custom(self):
        """
        Test generating a unit test workflow with custom configuration.
        
        This test verifies that the `generate_unit_test_workflow` function correctly
        creates a workflow dictionary when provided with custom parameters such as
        specific Python versions, operating systems, dependencies command, test
        command, branches, coverage flag, timeout, and codecov token. It checks that
        the resulting workflow contains the expected name, trigger branches,
        timeout, matrix configuration, steps for installing dependencies and running
        tests, and that no Codecov step is included when coverage is disabled.
        
        Args:
            self: The test case instance.
        
        Returns:
            None
        """
        workflow = generate_unit_test_workflow(
            name="My Tests",
            python_versions=["3.7", "3.11"],
            os_list=["macos-latest"],
            dependencies_command="poetry install",
            test_command="python -m unittest discover",
            branches=["develop"],
            coverage=False,
            timeout_minutes=30,
            codecov_token=True,
        )

        self.assertEqual(workflow["name"], "My Tests")
        self.assertEqual(workflow["on"]["push"]["branches"], ["develop"])
        self.assertEqual(workflow["jobs"]["test"]["timeout-minutes"], 30)
        self.assertEqual(workflow["jobs"]["test"]["strategy"]["matrix"]["os"], ["macos-latest"])
        self.assertEqual(
            workflow["jobs"]["test"]["strategy"]["matrix"]["python-version"],
            ["3.7", "3.11"],
        )
        self.assertEqual(
            workflow["jobs"]["test"]["steps"][2]["run"],
            "poetry install && pip install pytest pytest-cov",
        )
        self.assertEqual(
            workflow["jobs"]["test"]["steps"][3]["run"],
            "python -m unittest discover --cov=.",
        )
        self.assertNotIn(
            "codecov/codecov-action@v4",
            [step.get("uses", "") for step in workflow["jobs"]["test"]["steps"]],
        )  # No Codecov step

    def test_generate_unit_test_workflow_with_codecov_token(self):
        """
        Test that the unit test workflow generation correctly includes a Codecov token when the
        `codecov_token` flag is set to `True`.
        
        The test calls :func:`generate_unit_test_workflow` with ``codecov_token=True`` and
        verifies that the resulting workflow dictionary contains a `token` entry in the
        fifth step of the `test` job. It also checks that the token value is set to the
        expected GitHub Actions secret reference ``${{ secrets.CODECOV_TOKEN }}``.
        
        Parameters
        ----------
        self
        
        Returns
        -------
        None
        """
        workflow = generate_unit_test_workflow(codecov_token=True)
        self.assertIn("token", workflow["jobs"]["test"]["steps"][4]["with"])
        self.assertEqual(
            workflow["jobs"]["test"]["steps"][4]["with"]["token"],
            "${{ secrets.CODECOV_TOKEN }}",
        )


if __name__ == "__main__":
    unittest.main()
