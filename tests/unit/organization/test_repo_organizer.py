import os
from osa_tool.organization.repo_organizer import RepoOrganizer


class TestRepoOrganizer:
    def test_add_directories(self, tmp_path):
        repo_path = str(tmp_path)
        organizer = RepoOrganizer(repo_path)

        assert not os.path.exists(organizer.tests_dir)
        assert not os.path.exists(organizer.examples_dir)

        organizer.add_directories()
        assert os.path.exists(organizer.tests_dir)
        assert os.path.exists(organizer.examples_dir)

    def test_match_patterns(self):
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
