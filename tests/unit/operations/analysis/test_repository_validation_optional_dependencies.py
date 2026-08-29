import pytest

from osa_tool.operations.analysis.repository_validation import optional_dependencies


@pytest.mark.parametrize(
    "loader",
    [optional_dependencies.load_doc_validator, optional_dependencies.load_paper_validator],
)
def test_optional_repository_validation_loader_explains_installation(monkeypatch, loader):
    def raise_missing_dependency(_module_name):
        raise ImportError("missing torch")

    monkeypatch.setattr(optional_dependencies.importlib, "import_module", raise_missing_dependency)

    with pytest.raises(RuntimeError, match=r'pip install "osa_tool\[repository-validation\]"'):
        loader()
