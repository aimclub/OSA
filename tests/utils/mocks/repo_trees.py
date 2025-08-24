REPO_TREES: dict[str, str] = {
    "FULL": """
README.md
LICENSE
docs/index.rst
examples/example1.py
tests/test_main.py
CITATION.cff
CONTRIBUTING.md
requirements.txt
src/main.py
""".strip(),
    "MINIMAL": """
src/main.py
.gitignore
""".strip(),
    "WITH_TESTS": """
src/
src/main.py
tests/
tests/test_main.py
pytest.ini
""".strip(),
    "WITH_DOCS": """
docs/
docs/index.md
docs/api.rst
src/
src/main.py
""".strip(),
    "WITH_CITATION_ONLY": """
src/main.py
CITATION.bib
""".strip(),
    "WITH_CONTRIBUTING_ONLY": """
src/main.py
docs/
CONTRIBUTING.txt
""".strip(),
    "WITH_REQUIREMENTS_ONLY": """
src/
src/main.py
requirements.txt
""".strip(),
    "WITH_EXAMPLES_ONLY": """
src/main.py
tutorials/getting_started.ipynb
""".strip(),
    "LICENSE_ONLY": """
LICENSE.md
src/
src/main.py
""".strip(),
    "WITH_SETUP": """
setup.py
src/main.py
""".strip(),
    "WITH_PYPROJECT": """
pyproject.toml
src/main.py
""".strip(),
}


def get_mock_repo_tree(tree_type: str = "FULL") -> str:
    """Returns a mock repository tree by type"""
    return REPO_TREES[tree_type]
