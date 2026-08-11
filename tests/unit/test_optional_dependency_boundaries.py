import subprocess
import sys
import textwrap
from pathlib import Path

_OPTIONAL_MODULES = {
    "marker",
    "pypdf",
    "markdown_it",
    "rapidfuzz",
    "numpy",
    "scipy",
    "sentence_transformers",
    "torch",
    "torch_geometric",
    "transformers",
    "networkx",
    "matplotlib",
}


def test_core_imports_do_not_require_optional_feature_dependencies():
    script = textwrap.dedent(f"""
        import importlib.abc
        import sys

        blocked = {_OPTIONAL_MODULES!r}

        class OptionalDependencyBlocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split(".", 1)[0] in blocked:
                    raise ModuleNotFoundError(f"blocked optional dependency: {{fullname}}", name=fullname)

        sys.meta_path.insert(0, OptionalDependencyBlocker())
        import osa_tool.run
        import osa_tool.operations.operations_catalog
        import osa_tool.operations.analysis.paper_claims
        """)
    project_root = Path(__file__).resolve().parents[2]

    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
