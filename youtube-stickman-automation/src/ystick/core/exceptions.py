class YstickError(Exception):
    """Base class for all pipeline errors."""


class RetryableError(YstickError):
    """Transient failure (network, timeout, 5xx) — orchestrator will retry."""


class FatalError(YstickError):
    """Non-retryable failure (bad input, 4xx, missing config) — fails fast."""


class ApprovalPending(YstickError):
    """Raised internally when a stage needs a human decision that hasn't
    been recorded yet (used by stages that read approval files directly)."""
