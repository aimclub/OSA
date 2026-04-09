from osa_tool.operations.operations_catalog import register_all_operations
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
    assert "convert_notebooks" in names
