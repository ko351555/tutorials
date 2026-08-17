"""Retry policy shared by the orchestrator (whole-stage retries) and by
integration clients that want a tighter, call-specific retry (e.g. a single
HTTP request inside a stage that batches many of them)."""
from __future__ import annotations

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential_jitter,
)

from ystick.core.exceptions import RetryableError


def retrying(max_attempts: int = 5, initial: float = 2.0, max_wait: float = 60.0):
    """Decorator factory: retries only RetryableError, exponential backoff
    + jitter. FatalError and everything else propagate immediately —
    retrying a malformed request just burns quota for no benefit."""
    return retry(
        retry=retry_if_exception_type(RetryableError),
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential_jitter(initial=initial, max=max_wait),
        reraise=True,
    )
