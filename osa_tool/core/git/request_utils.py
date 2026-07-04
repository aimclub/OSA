"""HTTP request helper with exponential backoff retries for git-host API calls."""

from __future__ import annotations

import random
import time
from datetime import datetime
from email.utils import parsedate_to_datetime

import requests
from pydantic import BaseModel, ConfigDict, PositiveFloat, PositiveInt

from osa_tool.utils.logger import logger

RETRYABLE_STATUS = {500, 502, 503, 504}
RATE_LIMIT_STATUS = {429}
RETRYABLE_EXCEPTIONS = (requests.ConnectionError, requests.Timeout)
IDEMPOTENT_METHODS = {"get", "head", "options", "put", "delete"}


class RetryConfig(BaseModel):
    """Tunables for HTTP retry backoff."""

    model_config = ConfigDict(frozen=True)

    max_attempts: PositiveInt = 4
    backoff_base: PositiveFloat = 1.0
    backoff_factor: PositiveFloat = 2.0
    backoff_max_delay: PositiveFloat = 30.0
    backoff_total_cap: PositiveFloat = 120.0
    retry_after_max: PositiveFloat = 120.0
    request_timeout: PositiveFloat = 30.0


DEFAULT_RETRY_CONFIG = RetryConfig()


def _is_rate_limited(response: requests.Response) -> bool:
    if response.status_code in RATE_LIMIT_STATUS:
        return True
    return response.status_code == 403 and "rate limit" in response.text.lower()


def _parse_retry_after(response: requests.Response, cap: float) -> float | None:
    value = response.headers.get("Retry-After")
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            retry_dt = parsedate_to_datetime(value)
        except (TypeError, ValueError):
            return None
        seconds = (retry_dt - datetime.now(retry_dt.tzinfo)).total_seconds()
    return min(max(seconds, 0.0), cap)


def _backoff_delay(attempt: int, config: RetryConfig) -> float:
    raw = config.backoff_base * (config.backoff_factor ** (attempt - 1))
    return random.uniform(0, min(raw, config.backoff_max_delay))


def request_with_retry(
    method: str,
    url: str,
    *,
    retry_on_write: bool = False,
    config: RetryConfig | None = None,
    **request_kwargs,
) -> requests.Response:
    """Perform an HTTP request, retrying transient failures with exponential backoff.

    Rate limits (429, secondary 403) and connection errors are retried for any method;
    5xx responses and timeouts are retried only for idempotent methods or when
    ``retry_on_write`` is set. The ``Retry-After`` header overrides the computed delay.
    The final response is returned unchanged, so the caller's existing status handling
    still runs once retries are exhausted.

    Args:
        method (str): HTTP method, e.g. "get", "post", "put", "patch".
        url (str): Target URL.
        retry_on_write (bool): Allow retrying 5xx/timeout for non-idempotent methods.
        config (RetryConfig | None): Retry tunables; defaults to ``DEFAULT_RETRY_CONFIG``.
        **request_kwargs: Forwarded to the request (headers, json, params, timeout).

    Returns:
        requests.Response: The last response received.

    Raises:
        requests.RequestException: If the final attempt raises a transport error.
    """
    config = config or DEFAULT_RETRY_CONFIG
    request_kwargs.setdefault("timeout", config.request_timeout)
    write_allowed = retry_on_write or method.lower() in IDEMPOTENT_METHODS

    slept = 0.0
    response: requests.Response | None = None
    for attempt in range(1, config.max_attempts + 1):
        try:
            response = getattr(requests, method.lower())(url, **request_kwargs)
        except RETRYABLE_EXCEPTIONS as exc:
            ambiguous = isinstance(exc, requests.Timeout)
            if attempt == config.max_attempts or (ambiguous and not write_allowed):
                raise
            delay = _backoff_delay(attempt, config)
            if slept + delay > config.backoff_total_cap:
                raise
            logger.warning(
                f"Request to {url} failed ({exc.__class__.__name__}); "
                f"retrying in {delay:.1f}s (attempt {attempt}/{config.max_attempts})"
            )
            time.sleep(delay)
            slept += delay
            continue

        rate_limited = _is_rate_limited(response)
        server_error = response.status_code in RETRYABLE_STATUS
        if not rate_limited and not (server_error and write_allowed):
            return response
        if attempt == config.max_attempts:
            return response

        delay = _parse_retry_after(response, config.retry_after_max) if rate_limited else None
        if delay is None:
            delay = _backoff_delay(attempt, config)
        if slept + delay > config.backoff_total_cap:
            return response
        logger.warning(
            f"Request to {url} returned {response.status_code}; "
            f"retrying in {delay:.1f}s (attempt {attempt}/{config.max_attempts})"
        )
        time.sleep(delay)
        slept += delay

    return response
