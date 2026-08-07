"""Distinguishes genuine rate-limiting (worth retrying with backoff) from
quota/billing exhaustion (retrying can never fix it — fail fast instead).
Both surface as HTTP 429 from OpenAI/ElevenLabs-style APIs, but only one of
them is actually transient."""
from __future__ import annotations

_QUOTA_MARKERS = (
    "insufficient_quota",
    "credit_balance_exhausted",
    "quota_exceeded",
    "billing",
    "no credits remaining",
)


def is_quota_exhausted(status_code: int, body_text: str) -> bool:
    if status_code != 429:
        return False
    lowered = body_text.lower()
    return any(marker in lowered for marker in _QUOTA_MARKERS)
