import re


class TestAnalyzer:
    def __init__(
        self,
        tree: str,
        dependencies: list[str] | None = None,
        workflow_jobs: list[str] | None = None,
    ):
        self.tree = tree
        self.dependencies = [d.lower() for d in (dependencies or [])]
        self.workflow_jobs = workflow_jobs or []
        self.known_frameworks = ["pytest", "hypothesis"]  # todo extend this list

    def analyze(self) -> dict:
        return {
            "has_tests_dir": self._match(r"\btests?\b"),
            "has_test_files": self._match(r"test_.+\.py"),
            "frameworks": self._detect_frameworks(),
            "in_ci": any(re.search(r"test", job, re.IGNORECASE) for job in self.workflow_jobs),
        }

    def _detect_frameworks(self) -> list[str]:
        frameworks = set()

        for fw in self.known_frameworks:
            if fw in self.dependencies:
                frameworks.add(fw)

        return sorted(frameworks)

    def _match(self, pattern: str) -> bool:
        return bool(re.search(pattern, self.tree, re.IGNORECASE))
