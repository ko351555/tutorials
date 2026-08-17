"""One-time interactive OAuth2/PKCE authorization for Canva Connect —
separate from canva_client.py, which only ever *uses* an already-obtained
refresh token. No local redirect listener: the authorization URL sends the
browser to CANVA_REDIRECT_URI with ?code=... in the query string, and the
human pastes that URL (or just the code) back into the terminal. Simpler
and more portable than spinning up a temporary HTTP server, at the cost of
one manual copy-paste.

Run via `ystick canva-auth`.
"""
from __future__ import annotations

import base64
import hashlib
import os
import urllib.parse

import requests

from ystick.config import Secrets
from ystick.core.exceptions import FatalError

AUTHORIZATION_URL = "https://www.canva.com/api/oauth/authorize"
TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def generate_pkce_pair() -> tuple[str, str]:
    """Returns (code_verifier, code_challenge) per RFC 7636 (S256)."""
    verifier = _b64url(os.urandom(40))
    challenge = _b64url(hashlib.sha256(verifier.encode("ascii")).digest())
    return verifier, challenge


def generate_state() -> str:
    return _b64url(os.urandom(16))


def build_authorization_url(secrets: Secrets, state: str, code_challenge: str) -> str:
    if not secrets.canva_client_id:
        raise FatalError("CANVA_CLIENT_ID not set in .env — get one at canva.com/developers first.")
    params = {
        "client_id": secrets.canva_client_id,
        "redirect_uri": secrets.canva_redirect_uri,
        "response_type": "code",
        "scope": secrets.canva_scopes,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "state": state,
    }
    return f"{AUTHORIZATION_URL}?{urllib.parse.urlencode(params)}"


def extract_code_from_redirect(pasted: str, expected_state: str) -> str:
    """Accepts either the full redirected URL (the browser will show a
    "can't reach this page" error at CANVA_REDIRECT_URI, but the address
    bar still has the real URL — that's what to copy) or just the bare
    `code` value on its own."""
    pasted = pasted.strip()
    if not pasted.lower().startswith(("http://", "https://")):
        return pasted  # assume they pasted just the bare code

    parsed = urllib.parse.urlparse(pasted)
    qs = urllib.parse.parse_qs(parsed.query)
    if "error" in qs:
        desc = qs.get("error_description", [""])[0]
        raise FatalError(f"Canva returned an error: {qs['error'][0]} — {desc}")
    if "state" in qs and qs["state"][0] != expected_state:
        raise FatalError(
            "state mismatch — this doesn't look like the redirect from the "
            "authorization URL just printed. Run `ystick canva-auth` again "
            "from scratch and paste the URL from that specific attempt."
        )
    if "code" not in qs:
        raise FatalError(f"No 'code' parameter found in the pasted URL: {pasted[:200]}")
    return qs["code"][0]


def exchange_code_for_tokens(secrets: Secrets, code: str, code_verifier: str) -> dict:
    """Returns Canva's token response — {"access_token", "refresh_token",
    "expires_in", ...}. Only refresh_token matters to the caller; access
    tokens are short-lived and canva_client.py mints its own per call."""
    try:
        resp = requests.post(
            TOKEN_URL,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "code_verifier": code_verifier,
                "redirect_uri": secrets.canva_redirect_uri,
                "client_id": secrets.canva_client_id,
                "client_secret": secrets.canva_client_secret,
            },
            timeout=30,
        )
    except requests.RequestException as exc:
        raise FatalError(f"Canva token exchange request failed: {exc}") from exc
    if resp.status_code >= 400:
        raise FatalError(f"Canva token exchange failed ({resp.status_code}): {resp.text[:500]}")
    body = resp.json()
    if "refresh_token" not in body:
        raise FatalError(
            f"Canva's token response had no refresh_token — check that the "
            f"integration is requesting offline access. Raw response: {str(body)[:500]}"
        )
    return body
