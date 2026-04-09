from osa_tool.tools.repository_analysis.models import RepositoryData


def test_repository_data_defaults():
    # Act
    data = RepositoryData()

    # Assert
    assert data.dependencies is None
    assert data.python_version is None
    assert data.workflows is None
