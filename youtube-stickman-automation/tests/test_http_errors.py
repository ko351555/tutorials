from ystick.utils.http_errors import is_quota_exhausted


def test_openai_quota_exhausted_detected():
    body = '{"error": {"type": "insufficient_quota", "code": "credit_balance_exhausted"}}'
    assert is_quota_exhausted(429, body) is True


def test_genuine_rate_limit_not_quota_exhausted():
    body = '{"error": {"type": "rate_limit_exceeded", "message": "Too many requests"}}'
    assert is_quota_exhausted(429, body) is False


def test_non_429_never_quota_exhausted():
    body = '{"error": {"type": "insufficient_quota"}}'
    assert is_quota_exhausted(500, body) is False
