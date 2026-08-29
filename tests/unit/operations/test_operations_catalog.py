from osa_tool.operations.operations_catalog import (
    ConvertNotebooksOperation,
    DocValidationOperation,
    OrganizeRepositoryOperation,
    PaperValidationOperation,
    register_all_operations,
)
from osa_tool.operations import operations_catalog
from osa_tool.operations.registry import OperationRegistry


def test_register_all_operations_registers_known_operation():
    # Arrange
    saved = OperationRegistry._operations.copy()
    OperationRegistry._operations.clear()

    # Act
    try:
        register_all_operations(generate_docs=False)
        names = {o.name for o in OperationRegistry.list_all()}
    finally:
        OperationRegistry._operations.clear()
        OperationRegistry._operations.update(saved)

    # Assert
    assert "generate_report" in names
    assert "generate_notebook_report" in names
    assert "convert_notebooks" in names
    assert "validate_doc" in names
    assert "validate_paper" in names


def test_operation_dependencies_match_executor_signatures():
    assert ConvertNotebooksOperation.executor_dependencies == ["config_manager"]
    assert OrganizeRepositoryOperation.executor_dependencies == ["config_manager", "metadata"]


def test_organize_operation_description_reflects_safe_structural_reorganization():
    assert "group scattered source files" in OrganizeRepositoryOperation.description
    assert "without aggressive refactoring" in OrganizeRepositoryOperation.description


def test_validation_operations_load_optional_executors_only_when_called(monkeypatch):
    calls = []

    class FakeValidator:
        def __init__(self, **kwargs):
            calls.append(kwargs)

        def run(self):
            return {"result": "validated"}

    monkeypatch.setattr(operations_catalog, "load_doc_validator", lambda: FakeValidator)
    monkeypatch.setattr(operations_catalog, "load_paper_validator", lambda: FakeValidator)
    arguments = {
        "config_manager": object(),
        "git_agent": object(),
        "create_fork": False,
        "attachment": "attachment.pdf",
    }

    assert DocValidationOperation.executor(**arguments) == {"result": "validated"}
    assert PaperValidationOperation.executor(**arguments) == {"result": "validated"}
    assert calls == [arguments, arguments]
