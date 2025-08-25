import pytest


class DummyResponse:
    def __init__(self, content):
        self.content = content


class DummyLLMClient:

    @staticmethod
    def invoke(messages):
        return DummyResponse(content="sync response")

    @staticmethod
    async def ainvoke(messages):
        return DummyResponse(content="async response")


@pytest.fixture
def patch_llm_connector(monkeypatch):
    """Patch create_llm_connector to return a dummy client."""
    monkeypatch.setattr("osa_tool.models.models.create_llm_connector", lambda *args, **kwargs: DummyLLMClient())
