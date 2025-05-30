import unittest
from osa_tool.github_workflow.providers.black import generate_black_formatter_workflow


class TestBlackWorkflowGenerator(unittest.TestCase):

    def test_generate_black_formatter_workflow_default(self):
        workflow = generate_black_formatter_workflow()

        self.assertEqual(workflow["name"], "Black Formatter")
        self.assertEqual(
            workflow["on"], ["push", "pull_request"]
        )  # Default: all branches
        self.assertEqual(workflow["jobs"]["lint"]["name"], "Lint")
        self.assertEqual(workflow["jobs"]["lint"]["runs-on"], "ubuntu-latest")
        self.assertEqual(len(workflow["jobs"]["lint"]["steps"]), 2)
        self.assertEqual(
            workflow["jobs"]["lint"]["steps"][0]["uses"], "actions/checkout@v4"
        )
        self.assertEqual(
            workflow["jobs"]["lint"]["steps"][1]["name"], "Run Black"
        )  # Black step uses defaults
        self.assertEqual(
            workflow["jobs"]["lint"]["steps"][1]["uses"], "psf/black@stable"
        )
        self.assertEqual(
            workflow["jobs"]["lint"]["steps"][1]["with"]["options"], "--check --diff"
        )
        self.assertEqual(workflow["jobs"]["lint"]["steps"][1]["with"]["src"], ".")
        self.assertEqual(
            workflow["jobs"]["lint"]["steps"][1]["with"]["jupyter"], "false"
        )
        self.assertNotIn(
            "version", workflow["jobs"]["lint"]["steps"][1]["with"]
        )  # No version specified

    def test_generate_black_formatter_workflow_custom(self):
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
        self.assertEqual(
            workflow["on"]["push"]["branches"], ["main", "develop"]
        )  # Specific branches
        self.assertEqual(
            workflow["on"]["pull_request"]["branches"], ["main", "develop"]
        )  # Specific branches
        self.assertEqual(workflow["jobs"]["lint"]["name"], "Check Formatting")
        self.assertEqual(len(workflow["jobs"]["lint"]["steps"]), 3)
        self.assertEqual(
            workflow["jobs"]["lint"]["steps"][0]["uses"], "actions/checkout@v4"
        )
        self.assertEqual(workflow["jobs"]["lint"]["steps"][1]["name"], "Set up Python")
        self.assertEqual(
            workflow["jobs"]["lint"]["steps"][1]["with"]["python-version"], "3.9"
        )
        self.assertEqual(
            workflow["jobs"]["lint"]["steps"][2]["with"]["options"], "--line-length=79"
        )
        self.assertEqual(
            workflow["jobs"]["lint"]["steps"][2]["with"]["src"], "my_package/"
        )
        self.assertEqual(
            workflow["jobs"]["lint"]["steps"][2]["with"]["use_pyproject"], "true"
        )
        self.assertEqual(
            workflow["jobs"]["lint"]["steps"][2]["with"]["version"], "23.7.0"
        )
        self.assertEqual(
            workflow["jobs"]["lint"]["steps"][2]["with"]["jupyter"], "true"
        )


if __name__ == "__main__":
    unittest.main()
