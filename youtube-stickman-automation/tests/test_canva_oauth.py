import base64
import hashlib

import pytest

from ystick.config import Secrets
from ystick.core.exceptions import FatalError
from ystick.integrations import canva_oauth


def test_pkce_pair_challenge_matches_verifier():
    verifier, challenge = canva_oauth.generate_pkce_pair()
    expected_challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode("ascii")).digest()).rstrip(b"=").decode("ascii")
    assert challenge == expected_challenge
    # RFC 7636: verifier must be 43-128 chars of the unreserved character set.
    assert 43 <= len(verifier) <= 128


def test_pkce_pairs_are_random():
    v1, _ = canva_oauth.generate_pkce_pair()
    v2, _ = canva_oauth.generate_pkce_pair()
    assert v1 != v2


def test_build_authorization_url_includes_required_params():
    secrets = Secrets(canva_client_id="my-client-id", canva_redirect_uri="http://127.0.0.1:8765/callback")
    url = canva_oauth.build_authorization_url(secrets, state="the-state", code_challenge="the-challenge")

    assert url.startswith(canva_oauth.AUTHORIZATION_URL)
    assert "client_id=my-client-id" in url
    assert "code_challenge=the-challenge" in url
    assert "code_challenge_method=S256" in url
    assert "response_type=code" in url
    assert "state=the-state" in url


def test_build_authorization_url_requires_client_id():
    with pytest.raises(FatalError, match="CANVA_CLIENT_ID"):
        canva_oauth.build_authorization_url(Secrets(), state="s", code_challenge="c")


def test_extract_code_from_full_redirect_url():
    url = "http://127.0.0.1:8765/callback?code=abc123&state=the-state"
    assert canva_oauth.extract_code_from_redirect(url, expected_state="the-state") == "abc123"


def test_extract_code_from_bare_code_paste():
    assert canva_oauth.extract_code_from_redirect("just-the-code-value", expected_state="the-state") == "just-the-code-value"


def test_extract_code_rejects_state_mismatch():
    url = "http://127.0.0.1:8765/callback?code=abc123&state=wrong-state"
    with pytest.raises(FatalError, match="state mismatch"):
        canva_oauth.extract_code_from_redirect(url, expected_state="the-state")


def test_extract_code_surfaces_oauth_error():
    url = "http://127.0.0.1:8765/callback?error=access_denied&error_description=User+declined"
    with pytest.raises(FatalError, match="access_denied"):
        canva_oauth.extract_code_from_redirect(url, expected_state="the-state")


def test_extract_code_missing_code_param():
    url = "http://127.0.0.1:8765/callback?state=the-state"
    with pytest.raises(FatalError, match="No 'code' parameter"):
        canva_oauth.extract_code_from_redirect(url, expected_state="the-state")


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict):
        self.status_code = status_code
        self._json_body = json_body
        self.text = str(json_body)

    def json(self):
        return self._json_body


def test_exchange_code_for_tokens_request_shape(monkeypatch):
    captured = {}

    def fake_post(url, data=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        return _FakeResponse(200, {"access_token": "at", "refresh_token": "rt", "expires_in": 3600})

    monkeypatch.setattr(canva_oauth.requests, "post", fake_post)
    secrets = Secrets(canva_client_id="c", canva_client_secret="s", canva_redirect_uri="http://127.0.0.1:8765/callback")

    tokens = canva_oauth.exchange_code_for_tokens(secrets, code="the-code", code_verifier="the-verifier")

    assert tokens["refresh_token"] == "rt"
    assert captured["url"] == canva_oauth.TOKEN_URL
    assert captured["data"]["grant_type"] == "authorization_code"
    assert captured["data"]["code"] == "the-code"
    assert captured["data"]["code_verifier"] == "the-verifier"
    assert captured["data"]["redirect_uri"] == "http://127.0.0.1:8765/callback"


def test_exchange_code_for_tokens_requires_refresh_token_in_response(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        return _FakeResponse(200, {"access_token": "at", "expires_in": 3600})

    monkeypatch.setattr(canva_oauth.requests, "post", fake_post)
    secrets = Secrets(canva_client_id="c", canva_client_secret="s")

    with pytest.raises(FatalError, match="no refresh_token"):
        canva_oauth.exchange_code_for_tokens(secrets, code="the-code", code_verifier="the-verifier")


def test_exchange_code_for_tokens_failure(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        return _FakeResponse(400, {"error": "invalid_grant"})

    monkeypatch.setattr(canva_oauth.requests, "post", fake_post)
    secrets = Secrets(canva_client_id="c", canva_client_secret="s")

    with pytest.raises(FatalError, match="token exchange failed"):
        canva_oauth.exchange_code_for_tokens(secrets, code="bad-code", code_verifier="v")
