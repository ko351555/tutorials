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
    result = client.apply_branding(rough_cut, out_path, {"title": "t", "channel_name": "c"}, template_id="")

    assert result == out_path
    assert out_path.read_bytes() == b"FAKE_VIDEO_BYTES"


def test_apply_branding_mock_mode_passes_through(tmp_path: Path):
    rough_cut = tmp_path / "rough_cut.mp4"
    rough_cut.write_bytes(b"FAKE_VIDEO_BYTES")
    out_path = tmp_path / "09_final" / "branded_cut.mp4"

    client = CanvaClient(Secrets(), mock=True)
    result = client.apply_branding(rough_cut, out_path, {"title": "t", "channel_name": "c"}, template_id="tmpl_1")

    assert result == out_path
    assert out_path.read_bytes() == b"FAKE_VIDEO_BYTES"


def test_configured_requires_template_id_and_credentials():
    assert not CanvaClient(Secrets())._configured("tmpl_1")
    assert not CanvaClient(Secrets(canva_client_id="c", canva_client_secret="s"))._configured("")
    assert CanvaClient(
        Secrets(canva_client_id="client_1", canva_client_secret="secret_1")
    )._configured("tmpl_1")


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


def test_apply_branding_uses_the_passed_template_id_not_a_hardcoded_secret(tmp_path: Path, monkeypatch):
    """Real requirement: the long-form (16:9) and Shorts (9:16) videos need
    two different Canva Brand Templates, since Canva renders at whatever
    canvas size a template was built with. apply_branding() must use
    whichever template_id the caller passes, not a single fixed secret."""
    captured_template_ids = []

    def fake_post(url, headers=None, json=None, data=None, timeout=None):
        if url == canva_client_module.TOKEN_URL:
            return _FakeResponse(200, {"access_token": "tok"})
        if url == canva_client_module.AUTOFILL_URL:
            captured_template_ids.append(json["brand_template_id"])
            return _FakeResponse(200, {"design": {"id": "design-1"}})
        if url == canva_client_module.EXPORT_URL:
            return _FakeResponse(200, {"job": {"id": "job-1"}})
        raise AssertionError(f"unexpected POST {url}")

    def fake_get(url, headers=None, timeout=None):
        if url == f"{canva_client_module.EXPORT_URL}/job-1":
            return _FakeResponse(200, {"job": {"status": "success", "urls": ["https://example.com/clip.mp4"]}})
        return _FakeResponseWithContent()

    class _FakeResponseWithContent:
        content = b"FAKE_CLIP_BYTES"

    monkeypatch.setattr(canva_client_module.requests, "post", fake_post)
    monkeypatch.setattr(canva_client_module.requests, "get", fake_get)
    monkeypatch.setattr(canva_client_module, "run_ffmpeg", lambda cmd: None)

    rough_cut = tmp_path / "rough_cut.mp4"
    rough_cut.write_bytes(b"FAKE_VIDEO_BYTES")
    secrets = Secrets(canva_client_id="c", canva_client_secret="s", canva_refresh_token="rt")
    client = CanvaClient(secrets, mock=False)

    client.apply_branding(rough_cut, tmp_path / "out1.mp4", {"title": "t"}, template_id="LONGFORM_TEMPLATE")
    client.apply_branding(rough_cut, tmp_path / "out2.mp4", {"title": "t"}, template_id="SHORTS_TEMPLATE")

    # Two calls each (intro + outro) per apply_branding.
    assert captured_template_ids == [
        "LONGFORM_TEMPLATE", "LONGFORM_TEMPLATE", "SHORTS_TEMPLATE", "SHORTS_TEMPLATE",
    ]


def test_apply_branding_intro_and_outro_get_different_title_content(tmp_path: Path, monkeypatch):
    """Real gap fixed: intro and outro used to autofill identical data (same
    title, same everything), so both cards rendered the same. The outro
    should show a CTA instead of the video title, reusing the same "title"
    data field rather than requiring a second Canva-side field."""
    captured_data = []

    def fake_post(url, headers=None, json=None, data=None, timeout=None):
        if url == canva_client_module.TOKEN_URL:
            return _FakeResponse(200, {"access_token": "tok"})
        if url == canva_client_module.AUTOFILL_URL:
            captured_data.append(json["data"])
            return _FakeResponse(200, {"design": {"id": "design-1"}})
        if url == canva_client_module.EXPORT_URL:
            return _FakeResponse(200, {"job": {"id": "job-1"}})
        raise AssertionError(f"unexpected POST {url}")

    def fake_get(url, headers=None, timeout=None):
        if url == f"{canva_client_module.EXPORT_URL}/job-1":
            return _FakeResponse(200, {"job": {"status": "success", "urls": ["https://example.com/clip.mp4"]}})

        class _FakeResponseWithContent:
            content = b"FAKE_CLIP_BYTES"

        return _FakeResponseWithContent()

    monkeypatch.setattr(canva_client_module.requests, "post", fake_post)
    monkeypatch.setattr(canva_client_module.requests, "get", fake_get)
    monkeypatch.setattr(canva_client_module, "run_ffmpeg", lambda cmd: None)

    rough_cut = tmp_path / "rough_cut.mp4"
    rough_cut.write_bytes(b"FAKE_VIDEO_BYTES")
    secrets = Secrets(canva_client_id="c", canva_client_secret="s", canva_refresh_token="rt")
    client = CanvaClient(secrets, mock=False)

    client.apply_branding(
        rough_cut, tmp_path / "out.mp4",
        {"title": "5 AI Jobs That Will Vanish", "channel_name": "The Stickman Blueprint"},
        template_id="TEMPLATE_1",
    )

    intro_data, outro_data = captured_data
    assert intro_data["title"] == "5 AI Jobs That Will Vanish"
    assert outro_data["title"] != intro_data["title"]
    assert "The Stickman Blueprint" in outro_data["title"]
    assert intro_data["channel_name"] == outro_data["channel_name"] == "The Stickman Blueprint"


def test_apply_branding_respects_explicit_cta_text(tmp_path: Path, monkeypatch):
    captured_data = []

    def fake_post(url, headers=None, json=None, data=None, timeout=None):
        if url == canva_client_module.TOKEN_URL:
            return _FakeResponse(200, {"access_token": "tok"})
        if url == canva_client_module.AUTOFILL_URL:
            captured_data.append(json["data"])
            return _FakeResponse(200, {"design": {"id": "design-1"}})
        if url == canva_client_module.EXPORT_URL:
            return _FakeResponse(200, {"job": {"id": "job-1"}})
        raise AssertionError(f"unexpected POST {url}")

    def fake_get(url, headers=None, timeout=None):
        if url == f"{canva_client_module.EXPORT_URL}/job-1":
            return _FakeResponse(200, {"job": {"status": "success", "urls": ["https://example.com/clip.mp4"]}})

        class _FakeResponseWithContent:
            content = b"FAKE_CLIP_BYTES"

        return _FakeResponseWithContent()

    monkeypatch.setattr(canva_client_module.requests, "post", fake_post)
    monkeypatch.setattr(canva_client_module.requests, "get", fake_get)
    monkeypatch.setattr(canva_client_module, "run_ffmpeg", lambda cmd: None)

    rough_cut = tmp_path / "rough_cut.mp4"
    rough_cut.write_bytes(b"FAKE_VIDEO_BYTES")
    secrets = Secrets(canva_client_id="c", canva_client_secret="s", canva_refresh_token="rt")
    client = CanvaClient(secrets, mock=False)

    client.apply_branding(
        rough_cut, tmp_path / "out.mp4",
        {"title": "t", "channel_name": "c", "cta_text": "Hit follow for weekly frameworks"},
        template_id="TEMPLATE_1",
    )

    _, outro_data = captured_data
    assert outro_data["title"] == "Hit follow for weekly frameworks"
