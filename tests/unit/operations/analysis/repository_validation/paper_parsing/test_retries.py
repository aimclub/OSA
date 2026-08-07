import pytest

pytest.importorskip("doclayout_yolo", reason="paper_parsing optional dependency group is not installed")

import asyncio
import json
from types import SimpleNamespace

from osa_tool.operations.analysis.repository_validation.paper_parsing.doc_ocr import ImageDescription


class FlakyCompletions:
    """Fails the first ``failures`` calls, then answers."""

    def __init__(self, failures: int, error: Exception | None = None, content: str | None = "{}"):
        self.failures = failures
        self.error = error or ConnectionError("connection reset")
        self.content = content
        self.calls = 0

    async def create(self, **_):
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=self.content), finish_reason="stop")]
        )


def describer(failures=0, *, max_retries=3, content="{}", error=None) -> tuple[ImageDescription, FlakyCompletions]:
    element = {"image_bytes": "aGVsbG8=", "name": "plain text", "page_num": 0}
    describer = ImageDescription(
        use_async=True,
        bbox_json=[element],
        model_name="vlm",
        api_key="key",
        max_retries=max_retries,
        retry_delay=0.0,
    )
    completions = FlakyCompletions(failures, error=error, content=content)
    describer.model = SimpleNamespace(chat=SimpleNamespace(completions=completions))
    return describer, completions


def test_a_transient_error_no_longer_costs_the_element_its_text():
    d, completions = describer(failures=2)

    result = asyncio.run(d.inference_async(bbox_idx=0))

    assert result == "{}"
    assert completions.calls == 3


def test_retries_are_bounded_and_the_last_error_is_raised():
    d, completions = describer(failures=99, max_retries=2)

    with pytest.raises(ConnectionError, match="connection reset"):
        asyncio.run(d.inference_async(bbox_idx=0))

    assert completions.calls == 3  # the first attempt plus two retries


def test_an_empty_response_body_is_retried_too():
    """The SDK would never retry a 200 with no content, which is one way text was lost."""
    d, completions = describer(failures=0, content=None, max_retries=1)

    with pytest.raises(ValueError, match="Empty LLM content"):
        asyncio.run(d.inference_async(bbox_idx=0))

    assert completions.calls == 2


def test_retries_can_be_switched_off():
    d, completions = describer(failures=1, max_retries=0)

    with pytest.raises(ConnectionError):
        asyncio.run(d.inference_async(bbox_idx=0))

    assert completions.calls == 1


def test_cancellation_is_not_swallowed_by_the_retry_loop():
    d, _ = describer(failures=99, error=asyncio.CancelledError())

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(d.inference_async(bbox_idx=0))


def test_the_sdk_client_does_not_retry_underneath_us():
    d = ImageDescription(use_async=True, model_name="vlm", api_key="key", timeout=45.0)

    assert d.model.max_retries == 0
    assert d.model.timeout == 45.0
