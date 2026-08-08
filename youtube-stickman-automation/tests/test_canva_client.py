from pathlib import Path

import pytest

from ystick.config import Secrets
from ystick.core.exceptions import FatalError
from ystick.integrations import canva_client as canva_client_module
from ystick.integrations.canva_client import CanvaClient


def test_apply_branding_skips_gracefully_when_not_configured(tmp_path: Path):
    """Real production case: no Canva Connect app / brand template set up
    yet. Branding is an enhancement, not the deliverable — the rough cut
    should pass through unbranded instead of blocking the pipeline."""
    rough_cut = tmp_path / "rough_cut.mp4"
    rough_cut.write_bytes(b"FAKE_VIDEO_BYTES")
    out_path = tmp_path / "09_final" / "branded_cut.mp4"

    client = CanvaClient(Secrets(), mock=False)
    result = client.apply_branding(rough_cut, out_path, {"title": "t", "channel_name": "c"})

    assert result == out_path
    assert out_path.read_bytes() == b"FAKE_VIDEO_BYTES"


def test_apply_branding_mock_mode_passes_through(tmp_path: Path):
    rough_cut = tmp_path / "rough_cut.mp4"
    rough_cut.write_bytes(b"FAKE_VIDEO_BYTES")
    out_path = tmp_path / "09_final" / "branded_cut.mp4"

    client = CanvaClient(Secrets(), mock=True)
    result = client.apply_branding(rough_cut, out_path, {"title": "t", "channel_name": "c"})

    assert result == out_path
    assert out_path.read_bytes() == b"FAKE_VIDEO_BYTES"


def test_configured_requires_all_three_credentials():
    assert not CanvaClient(Secrets())._configured()
    assert not CanvaClient(Secrets(canva_brand_template_id="tmpl_1"))._configured()
    assert CanvaClient(
        Secrets(
            canva_brand_template_id="tmpl_1",
            canva_client_id="client_1",
            canva_client_secret="secret_1",
        )
    )._configured()


def test_access_token_without_refresh_token_points_to_canva_auth():
    client = CanvaClient(Secrets(canva_client_id="c", canva_client_secret="s"), mock=False)
    with pytest.raises(FatalError, match="ystick canva-auth"):
        client._access_token()


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict):
        self.status_code = status_code
        self._json_body = json_body
        self.text = str(json_body)

    def json(self):
        return self._json_body


def test_access_token_refreshes_using_stored_refresh_token(monkeypatch):
    captured = {}

    def fake_post(url, data=None, timeout=None):
        captured["url"] = url
        captured["data"] = data
        return _FakeResponse(200, {"access_token": "fresh-access-token", "expires_in": 3600})

    monkeypatch.setattr(canva_client_module.requests, "post", fake_post)

    client = CanvaClient(
        Secrets(canva_client_id="c", canva_client_secret="s", canva_refresh_token="stored-refresh"),
        mock=False,
    )
    token = client._access_token()

    assert token == "fresh-access-token"
    assert captured["url"] == canva_client_module.TOKEN_URL
    assert captured["data"]["grant_type"] == "refresh_token"
    assert captured["data"]["refresh_token"] == "stored-refresh"
    assert captured["data"]["client_id"] == "c"
    assert captured["data"]["client_secret"] == "s"


def test_access_token_expired_refresh_token_gives_actionable_error(monkeypatch):
    def fake_post(url, data=None, timeout=None):
        return _FakeResponse(400, {"error": "invalid_grant"})

    monkeypatch.setattr(canva_client_module.requests, "post", fake_post)

    client = CanvaClient(
        Secrets(canva_client_id="c", canva_client_secret="s", canva_refresh_token="stale"),
        mock=False,
    )
    with pytest.raises(FatalError, match="ystick canva-auth"):
        client._access_token()
