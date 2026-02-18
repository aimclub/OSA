import os
from osa_tool.organization.repo_organizer import RepoOrganizer


class TestRepoOrganizer:
    """
    TestRepoOrganizer
    
    Test class for RepoOrganizer, providing unit tests for directory creation, pattern matching, file moving, organization, and exclusion logic.
    
    Methods:
        test_add_directories
        test_match_patterns
        test_move_files_by_patterns
        test_organize
        test_exclude_directories
    
    Attributes:
        None
    
    Each method verifies a specific behavior of RepoOrganizer in a temporary repository context.
    """
    def test_add_directories(self, tmp_path):
        """
        Test that RepoOrganizer.add_directories correctly creates the 'tests' and 'examples' directories.
        
        This method verifies the behavior of the RepoOrganizer's add_directories method by:
        1. Instantiating a RepoOrganizer with a temporary repository path.
        2. Asserting that the 'tests' and 'examples' directories do not exist initially.
        3. Calling add_directories to create the directories.
        4. Asserting that the directories now exist.
        
        Args:
            self: The test instance.
            tmp_path: A temporary directory path provided by the testing framework (e.g., pytest's tmp_path fixture).
        
        Returns:
            None
        """
        repo_path = str(tmp_path)
        organizer = RepoOrganizer(repo_path)

        assert not os.path.exists(organizer.tests_dir)
        assert not os.path.exists(organizer.examples_dir)

        organizer.add_directories()
        assert os.path.exists(organizer.tests_dir)
        assert os.path.exists(organizer.examples_dir)

    def test_match_patterns(self):
        """
        Test the pattern matching logic of RepoOrganizer.
        
        This method verifies that the `match_patterns` method correctly identifies
        files that match predefined test and example filename patterns. It creates
        a `RepoOrganizer` instance with an empty repository path and then
        asserts that various filenames are matched or not matched against the
        `TEST_PATTERNS` and `EXAMPLE_PATTERNS` lists.
        
        Args:
            self: The test case instance.
        
        Returns:
            None
        """
        organizer = RepoOrganizer("")

        assert organizer.match_patterns("test_file.py", organizer.TEST_PATTERNS)
        assert organizer.match_patterns("file_test.py", organizer.TEST_PATTERNS)
        assert not organizer.match_patterns("file.py", organizer.TEST_PATTERNS)
        assert organizer.match_patterns("TEST_file.py", organizer.TEST_PATTERNS)
        assert organizer.match_patterns("file_TEST.py", organizer.TEST_PATTERNS)

        assert organizer.match_patterns("example.py", organizer.EXAMPLE_PATTERNS)
        assert organizer.match_patterns("my_example.py", organizer.EXAMPLE_PATTERNS)
        assert organizer.match_patterns("sample_code.py", organizer.EXAMPLE_PATTERNS)
        assert organizer.match_patterns("demo_app.py", organizer.EXAMPLE_PATTERNS)
        assert not organizer.match_patterns("file.py", organizer.EXAMPLE_PATTERNS)

    def test_move_files_by_patterns(self, tmp_path):
        """
        Test moving files by patterns in a repository.
        
        This test creates a temporary repository structure containing a test file and a normal file. It then initializes a `RepoOrganizer`, ensures the required directories exist, and calls `move_files_by_patterns` to relocate files that match the test patterns into the tests directory. Finally, it asserts that the test file has been moved while the normal file remains in its original location.
        
        Parameters
        ----------
        self
            The test instance.
        tmp_path
            Temporary directory path provided by pytest.
        
        Returns
        -------
        None
        """
        repo_path = str(tmp_path)

        test_file_path = os.path.join(repo_path, "test_file.py")
        normal_file_path = os.path.join(repo_path, "normal_file.py")

        with open(test_file_path, "w") as f:
            f.write("# Test file")
        with open(normal_file_path, "w") as f:
            f.write("# Normal file")

        organizer = RepoOrganizer(repo_path)
        organizer.add_directories()
        organizer.move_files_by_patterns(organizer.tests_dir, organizer.TEST_PATTERNS)

        assert not os.path.exists(test_file_path)
        assert os.path.exists(os.path.join(organizer.tests_dir, "test_file.py"))
        assert os.path.exists(normal_file_path)

    def test_organize(self, tmp_path):
        """
        Test the repository organization process.
        
        This method creates a temporary repository structure with a test file, an example file,
        and a normal file. It then instantiates a :class:`RepoOrganizer` with the temporary
        path, calls its :meth:`organize` method, and verifies that the test and example
        files are moved into the appropriate ``tests`` and ``examples`` directories,
        respectively, while the normal file remains in the root directory.
        
        Parameters
        ----------
        self
            The test case instance.
        tmp_path
            A temporary directory path provided by the test framework (e.g., pytest's
            ``tmp_path`` fixture). The path is used as the root of the mock repository.
        
        Returns
        -------
        None
            This method performs assertions and does not return a value.
        """
        repo_path = str(tmp_path)

        test_file_path = os.path.join(repo_path, "test_file.py")
        example_file_path = os.path.join(repo_path, "example_code.py")
        normal_file_path = os.path.join(repo_path, "normal_file.py")
        with open(test_file_path, "w") as f:
            f.write("# Test file")
        with open(example_file_path, "w") as f:
            f.write("# Example file")
        with open(normal_file_path, "w") as f:
            f.write("# Normal file")

        organizer = RepoOrganizer(repo_path)
        organizer.organize()

        assert os.path.exists(organizer.tests_dir)
        assert os.path.exists(organizer.examples_dir)
        assert not os.path.exists(test_file_path)
        assert not os.path.exists(example_file_path)
        assert os.path.exists(normal_file_path)
        assert os.path.exists(os.path.join(organizer.tests_dir, "test_file.py"))
        assert os.path.exists(os.path.join(organizer.examples_dir, "example_code.py"))

    def test_exclude_directories(self, tmp_path):
        """
        Test that files in excluded directories are not moved by RepoOrganizer.
        
        Parameters
        ----------
        self
            The test instance.
        tmp_path
            Temporary directory path provided by pytest.
        
        This test creates a `.git` directory inside the temporary repository path, writes a test file into it, then runs the `RepoOrganizer.organize()` method. It verifies that the file remains in the `.git` directory and is not relocated to the `tests` directory.
        
        Returns
        -------
        None
        """
        repo_path = str(tmp_path)
        excluded_dir = os.path.join(repo_path, ".git")
        os.makedirs(excluded_dir)
        test_file_path = os.path.join(excluded_dir, "test_excluded.py")
        with open(test_file_path, "w") as f:
            f.write("# Test file in excluded directory")
        organizer = RepoOrganizer(repo_path)
        organizer.organize()

        assert os.path.exists(test_file_path)
        assert not os.path.exists(os.path.join(organizer.tests_dir, "test_excluded.py"))
