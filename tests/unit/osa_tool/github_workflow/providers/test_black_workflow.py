import unittest
from osa_tool.github_workflow.providers.black import generate_black_formatter_workflow


class TestBlackWorkflowGenerator(unittest.TestCase):
    """
    TestBlackWorkflowGenerator
    
    This test suite verifies the generation of GitHub Actions workflows for the Black formatter. It ensures that both default and custom configurations produce the expected workflow dictionaries.
    
    Class Methods:
    - test_generate_black_formatter_workflow_default:
    """

    def test_generate_black_formatter_workflow_default(self):
        """
        Test the default configuration of the Black formatter workflow generator.
        
        This method verifies that calling :func:`generate_black_formatter_workflow` with no
        explicit arguments produces a workflow dictionary that matches the expected
        default values. It checks the workflow name, trigger events, job configuration,
        and the properties of the Black step, ensuring that the defaults for options,
        source directory, Jupyter support, and version handling are correctly applied.
        
        Parameters
        ----------
        self
            The test case instance.
        
        Returns
        -------
        None
            This test method does not return a value; it uses assertions to validate
            the generated workflow configuration.
        """
        workflow = generate_black_formatter_workflow()

        self.assertEqual(workflow["name"], "Black Formatter")
        self.assertEqual(workflow["on"], ["push", "pull_request"])  # Default: all branches
        self.assertEqual(workflow["jobs"]["lint"]["name"], "Lint")
        self.assertEqual(workflow["jobs"]["lint"]["runs-on"], "ubuntu-latest")
        self.assertEqual(len(workflow["jobs"]["lint"]["steps"]), 2)
        self.assertEqual(workflow["jobs"]["lint"]["steps"][0]["uses"], "actions/checkout@v4")
        self.assertEqual(workflow["jobs"]["lint"]["steps"][1]["name"], "Run Black")  # Black step uses defaults
        self.assertEqual(workflow["jobs"]["lint"]["steps"][1]["uses"], "psf/black@stable")
        self.assertEqual(workflow["jobs"]["lint"]["steps"][1]["with"]["options"], "--check --diff")
        self.assertEqual(workflow["jobs"]["lint"]["steps"][1]["with"]["src"], ".")
        self.assertEqual(workflow["jobs"]["lint"]["steps"][1]["with"]["jupyter"], "false")
        self.assertNotIn("version", workflow["jobs"]["lint"]["steps"][1]["with"])  # No version specified

    def test_generate_black_formatter_workflow_custom(self):
        """
        Test generating a custom Black formatter workflow.
        
        This test verifies that `generate_black_formatter_workflow` correctly constructs a GitHub Actions
        workflow dictionary when provided with custom parameters such as name, job_name, branches,
        black_options, src, use_pyproject, version, jupyter, and python_version. It asserts that the
        resulting workflow contains the expected name, trigger branches, job name, and step
        configurations, including the correct options passed to the Black action and the use of a
        specific Python version.
        
        Parameters
        ----------
        self
        
        Returns
        -------
        None
        """
        workflow = generate_black_formatter_workflow(
            name="Custom Black",
            job_name="Check Formatting",
            branches=["main", "develop"],
            black_options="--line-length=79",
            src="my_package/",
            use_pyproject=True,
            version="23.7.0",  # Example version
            jupyter=True,
            python_version="3.9",
        )

        self.assertEqual(workflow["name"], "Custom Black")
        self.assertEqual(workflow["on"]["push"]["branches"], ["main", "develop"])  # Specific branches
        self.assertEqual(workflow["on"]["pull_request"]["branches"], ["main", "develop"])  # Specific branches
        self.assertEqual(workflow["jobs"]["lint"]["name"], "Check Formatting")
        self.assertEqual(len(workflow["jobs"]["lint"]["steps"]), 3)
        self.assertEqual(workflow["jobs"]["lint"]["steps"][0]["uses"], "actions/checkout@v4")
        self.assertEqual(workflow["jobs"]["lint"]["steps"][1]["name"], "Set up Python")
        self.assertEqual(workflow["jobs"]["lint"]["steps"][1]["with"]["python-version"], "3.9")
        self.assertEqual(workflow["jobs"]["lint"]["steps"][2]["with"]["options"], "--line-length=79")
        self.assertEqual(workflow["jobs"]["lint"]["steps"][2]["with"]["src"], "my_package/")
        self.assertEqual(workflow["jobs"]["lint"]["steps"][2]["with"]["use_pyproject"], "true")
        self.assertEqual(workflow["jobs"]["lint"]["steps"][2]["with"]["version"], "23.7.0")
        self.assertEqual(workflow["jobs"]["lint"]["steps"][2]["with"]["jupyter"], "true")


if __name__ == "__main__":
    unittest.main()
