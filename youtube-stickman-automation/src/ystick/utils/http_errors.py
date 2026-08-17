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

# Deliberately NOT matching Gemini's "RESOURCE_EXHAUSTED" / "Quota exceeded"
# wording here — on Gemini that status covers both permanent (daily quota
# gone) and transient (per-minute rate limit) cases with near-identical
# text, and misclassifying a transient one as fatal would stop a retry that
# was about to succeed. Gemini 429s fall through to the normal retry path
# below; a truly exhausted quota still ends in "failed" either way, just
# after the backoff window instead of immediately.


def is_quota_exhausted(status_code: int, body_text: str) -> bool:
    if status_code != 429:
        return False
    lowered = body_text.lower()
    return any(marker in lowered for marker in _QUOTA_MARKERS)
