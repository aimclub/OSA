import subprocess
import sys
import textwrap
from pathlib import Path

_OPTIONAL_MODULES = {
    "marker",
    "mcp",
    "pypdf",
    "markdown_it",
    "rapidfuzz",
    "numpy",
    "scipy",
    "sentence_transformers",
    "torch",
}


def _run_without_optional_dependencies(statements: str) -> subprocess.CompletedProcess[str]:
    script = textwrap.dedent(
        f"""
        import importlib.abc
        import sys

        blocked = {_OPTIONAL_MODULES!r}

        class OptionalDependencyBlocker(importlib.abc.MetaPathFinder):
            def find_spec(self, fullname, path=None, target=None):
                if fullname.split(".", 1)[0] in blocked:
                    raise ModuleNotFoundError(f"blocked optional dependency: {{fullname}}", name=fullname)

        sys.meta_path.insert(0, OptionalDependencyBlocker())
        """
    )
    project_root = Path(__file__).resolve().parents[2]
    return subprocess.run(
        [sys.executable, "-c", script + textwrap.dedent(statements)],
        cwd=project_root,
        capture_output=True,
        text=True,
        check=False,
    )


def test_core_imports_do_not_require_optional_feature_dependencies() -> None:
    """Keep the regular CLI and operation discovery independent of optional features."""
    result = _run_without_optional_dependencies(
        """
        import osa_tool.run
        import osa_tool.operations.operations_catalog
        import osa_tool.operations.analysis.paper_claims
        assert 'osa_tool.mcp_server' not in sys.modules
        assert 'osa_tool.operations.analysis.repository_quality.assessment' not in sys.modules
        """
    )
    assert result.returncode == 0, result.stderr


def test_mcp_launcher_explains_missing_extra() -> None:
    """Report how to install the extra instead of printing an import traceback."""
    result = _run_without_optional_dependencies("from osa_tool.mcp_cli import main\nmain()")
    assert result.returncode == 1
    assert 'uv pip install "osa_tool[mcp]"' in result.stderr
    assert "Traceback" not in result.stderr
