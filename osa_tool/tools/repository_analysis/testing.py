import re


class TestAnalyzer:
    """
    A class for analyzing the testing setup of a repository.
    
        This class examines a provided tree structure and dependency list to determine the presence and configuration of tests, including directory structure, test files, supported frameworks, and CI integration.
    
        Attributes:
            tree: Stores the tree structure representation of the repository.
            dependencies: A list of lowercase dependency names used for framework detection.
            workflow_jobs: A list of jobs associated with CI workflows to check for test runs.
            known_frameworks: A list of supported testing frameworks (e.g., pytest, hypothesis).
    
        Methods:
            __init__: Initializes the analyzer with repository structure and dependency data.
            analyze: Performs the main analysis and returns a summary dictionary.
            _detect_frameworks: Identifies which known frameworks are present in dependencies.
            _match: Checks if a regex pattern matches the internal tree string.
    """

    def __init__(
        self,
        tree: str,
        dependencies: list[str] | None = None,
        workflow_jobs: list[str] | None = None,
    ):
        """
        Initialize a new instance of the TestAnalyzer with tree structure and dependency information.
        
        Args:
            tree: The tree structure representation of the code or tests to be analyzed.
            dependencies: A list of dependency names to be tracked. If not provided, defaults to an empty list.
            workflow_jobs: A list of workflow job identifiers associated with the instance. If not provided, defaults to an empty list.
        
        Attributes:
            tree: Stores the provided tree structure representation.
            dependencies: A list of lowercase dependency names. Dependencies are converted to lowercase to ensure case-insensitive tracking.
            workflow_jobs: A list of jobs associated with the workflow.
            known_frameworks: A list of supported testing frameworks, currently including pytest and hypothesis. This list is intended to be extended in the future.
        """
        self.tree = tree
        self.dependencies = [d.lower() for d in (dependencies or [])]
        self.workflow_jobs = workflow_jobs or []
        self.known_frameworks = ["pytest", "hypothesis"]  # todo extend this list

    def analyze(self) -> dict:
        """
        Analyzes the repository's testing setup and returns a summary.
        
        The method checks for the presence of a tests directory, test files, common
        testing frameworks, and whether testing is configured in CI workflows.
        
        Returns:
            dict: A dictionary containing the analysis results with the following keys:
                has_tests_dir (bool): Indicates if a directory named 'test' or 'tests' exists.
                    This is determined by a case-insensitive regex match for 'test' or 'tests' in the repository's tree structure.
                has_test_files (bool): Indicates if any Python files prefixed with 'test_' exist.
                    This is determined by a case-insensitive regex match for filenames starting with 'test_' and ending with '.py' in the repository's tree structure.
                frameworks (list[str]): A sorted list of detected testing frameworks.
                    Frameworks are identified by checking the project's dependencies against a known list of common testing frameworks.
                in_ci (bool): Indicates if any CI workflow job name contains the word 'test' (case-insensitive).
                    This checks the list of workflow job names provided during the analyzer's initialization.
        """
        return {
            "has_tests_dir": self._match(r"\btests?\b"),
            "has_test_files": self._match(r"test_.+\.py"),
            "frameworks": self._detect_frameworks(),
            "in_ci": any(re.search(r"test", job, re.IGNORECASE) for job in self.workflow_jobs),
        }

    def _detect_frameworks(self) -> list[str]:
        """
        Identifies which known frameworks are present in the current dependencies.
        
        The method iterates through a predefined list of known frameworks (stored in `self.known_frameworks`) and checks for their existence within the object's dependencies (`self.dependencies`). This detection is used to tailor subsequent analysis or documentation based on the frameworks actually used in the project. It returns a sorted list of unique matches.
        
        Returns:
            list[str]: A sorted list of framework names detected in the dependencies.
        """
        frameworks = set()

        for fw in self.known_frameworks:
            if fw in self.dependencies:
                frameworks.add(fw)

        return sorted(frameworks)

    def _match(self, pattern: str) -> bool:
        """
        Checks if a given regular expression pattern matches the internal tree string.
        
        Args:
            pattern: The regular expression pattern to search for within the tree.
        
        Returns:
            bool: True if the pattern is found anywhere within the tree string (case-insensitive), False otherwise.
        
        Note:
            The search is performed using `re.search` with the `re.IGNORECASE` flag, meaning the match is case-insensitive and only requires a substring match anywhere in the tree string.
        """
        return bool(re.search(pattern, self.tree, re.IGNORECASE))
