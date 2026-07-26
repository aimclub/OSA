from contextlib import contextmanager
from unittest.mock import Mock, patch

import pytest
import requests

from osa_tool.core.git.request_utils import RetryConfig, request_with_retry
from tests.utils.mocks.requests_mock import mock_requests_response

TEST_CONFIG = RetryConfig(
    max_attempts=4,
    backoff_base=1.0,
    backoff_factor=2.0,
    backoff_max_delay=30.0,
    backoff_total_cap=120.0,
    retry_after_max=60.0,
    request_timeout=5.0,
)

URL = "https://api.example.com/resource"


@contextmanager
def patched(side_effect, jitter=0.0):
    caller = Mock(side_effect=side_effect)
    with (
        patch("osa_tool.core.git.request_utils.requests.get", caller),
        patch("osa_tool.core.git.request_utils.requests.post", caller),
        patch("osa_tool.core.git.request_utils.requests.put", caller),
        patch("osa_tool.core.git.request_utils.requests.patch", caller),
        patch("osa_tool.core.git.request_utils.time.sleep") as sleep,
        patch("osa_tool.core.git.request_utils.random.uniform", return_value=jitter),
    ):
        yield caller, sleep


def test_retries_rate_limit_then_succeeds():
    # Arrange
    responses = [mock_requests_response(429), mock_requests_response(200, json_data={"ok": True})]

    # Act
    with patched(responses) as (request, sleep):
        result = request_with_retry("get", URL, config=TEST_CONFIG)

    # Assert
    assert result.status_code == 200
    assert request.call_count == 2
    assert sleep.call_count == 1


def test_returns_final_response_when_retries_exhausted():
    # Arrange
    responses = [mock_requests_response(503) for _ in range(TEST_CONFIG.max_attempts)]

    # Act
    with patched(responses) as (request, sleep):
        result = request_with_retry("get", URL, config=TEST_CONFIG)

    # Assert
    assert result.status_code == 503
    assert request.call_count == TEST_CONFIG.max_attempts
    assert sleep.call_count == TEST_CONFIG.max_attempts - 1
    with pytest.raises(requests.HTTPError):
        result.raise_for_status()


def test_honors_retry_after_header():
    # Arrange
    responses = [mock_requests_response(429, headers={"Retry-After": "7"}), mock_requests_response(200)]

    # Act
    with patched(responses) as (_, sleep):
        request_with_retry("get", URL, config=TEST_CONFIG)

    # Assert
    sleep.assert_called_once_with(7.0)


def test_clamps_retry_after_to_max():
    # Arrange
    responses = [mock_requests_response(429, headers={"Retry-After": "999"}), mock_requests_response(200)]

    # Act
    with patched(responses) as (_, sleep):
        request_with_retry("get", URL, config=TEST_CONFIG)

    # Assert
    sleep.assert_called_once_with(TEST_CONFIG.retry_after_max)


def test_does_not_retry_non_retryable_status():
    # Arrange
    responses = [mock_requests_response(404)]

    # Act
    with patched(responses) as (request, sleep):
        result = request_with_retry("get", URL, config=TEST_CONFIG)

    # Assert
    assert result.status_code == 404
    assert request.call_count == 1
    sleep.assert_not_called()


def test_retries_secondary_rate_limit_in_body():
    # Arrange
    responses = [mock_requests_response(403, text_data="API rate limit exceeded"), mock_requests_response(200)]

    # Act
    with patched(responses) as (request, _):
        result = request_with_retry("get", URL, config=TEST_CONFIG)

    # Assert
    assert result.status_code == 200
    assert request.call_count == 2


def test_does_not_retry_permission_403():
    # Arrange
    responses = [mock_requests_response(403, text_data="permission denied")]

    # Act
    with patched(responses) as (request, _):
        result = request_with_retry("get", URL, config=TEST_CONFIG)

    # Assert
    assert result.status_code == 403
    assert request.call_count == 1


def test_retries_connection_error():
    # Arrange
    responses = [requests.ConnectionError(), mock_requests_response(200)]

    # Act
    with patched(responses) as (request, _):
        result = request_with_retry("get", URL, config=TEST_CONFIG)

    # Assert
    assert result.status_code == 200
    assert request.call_count == 2


def test_timeout_on_write_not_retried_by_default():
    # Arrange
    responses = [requests.Timeout(), mock_requests_response(200)]

    # Act / Assert
    with patched(responses) as (request, _):
        with pytest.raises(requests.Timeout):
            request_with_retry("post", URL, config=TEST_CONFIG)
    assert request.call_count == 1


def test_timeout_on_write_retried_when_opted_in():
    # Arrange
    responses = [requests.Timeout(), mock_requests_response(201)]

    # Act
    with patched(responses) as (request, _):
        result = request_with_retry("post", URL, retry_on_write=True, config=TEST_CONFIG)

    # Assert
    assert result.status_code == 201
    assert request.call_count == 2


def test_server_error_on_write_not_retried_by_default():
    # Arrange
    responses = [mock_requests_response(503), mock_requests_response(201)]

    # Act
    with patched(responses) as (request, _):
        result = request_with_retry("post", URL, config=TEST_CONFIG)

    # Assert
    assert result.status_code == 503
    assert request.call_count == 1


def test_rate_limit_on_write_always_retried():
    # Arrange
    responses = [mock_requests_response(429), mock_requests_response(201)]

    # Act
    with patched(responses) as (request, _):
        result = request_with_retry("post", URL, config=TEST_CONFIG)

    # Assert
    assert result.status_code == 201
    assert request.call_count == 2


def test_respects_total_backoff_cap():
    # Arrange
    config = RetryConfig(max_attempts=10, backoff_total_cap=5.0, retry_after_max=60.0)
    responses = [mock_requests_response(503) for _ in range(10)]

    # Act
    with patched(responses, jitter=3.0) as (request, sleep):
        result = request_with_retry("get", URL, config=config)

    # Assert
    assert result.status_code == 503
    assert sleep.call_count == 1
    assert request.call_count == 2


def test_uses_max_attempts_from_config():
    # Arrange
    config = RetryConfig(max_attempts=2, retry_after_max=60.0)
    responses = [mock_requests_response(429), mock_requests_response(429), mock_requests_response(200)]

    # Act
    with patched(responses) as (request, _):
        result = request_with_retry("get", URL, config=config)

    # Assert
    assert result.status_code == 429
    assert request.call_count == 2


def test_forwards_kwargs_and_injects_timeout():
    # Arrange
    responses = [mock_requests_response(200)]
    headers = {"Authorization": "token abc"}

    # Act
    with patched(responses) as (request, _):
        request_with_retry("get", URL, headers=headers, config=TEST_CONFIG)

    # Assert
    request.assert_called_once_with(URL, headers=headers, timeout=TEST_CONFIG.request_timeout)


def test_keeps_caller_timeout():
    # Arrange
    responses = [mock_requests_response(200)]

    # Act
    with patched(responses) as (request, _):
        request_with_retry("get", URL, timeout=99, config=TEST_CONFIG)

    # Assert
    assert request.call_args.kwargs["timeout"] == 99
