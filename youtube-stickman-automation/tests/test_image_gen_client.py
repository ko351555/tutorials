import base64
from pathlib import Path

import pytest

from ystick.config import Secrets
from ystick.core.exceptions import FatalError
from ystick.integrations import image_gen_client as igc_module
from ystick.integrations.image_gen_client import ImageGenClient


def test_mock_mode_ignores_provider(tmp_path: Path):
    client = ImageGenClient(Secrets(image_gen_provider="gemini"), mock=True)
    out_path = tmp_path / "scene_001" / "image.png"
    result = client.generate("a stickman", out_path)
    assert result == out_path
    assert out_path.exists()
    assert out_path.stat().st_size > 0


def test_openai_provider_fails_fast_without_key(tmp_path: Path):
    client = ImageGenClient(Secrets(image_gen_provider="openai", image_gen_api_key=""), mock=False)
    with pytest.raises(FatalError, match="IMAGE_GEN_API_KEY"):
        client.generate("a stickman", tmp_path / "image.png")


def test_gemini_provider_fails_fast_without_key(tmp_path: Path):
    client = ImageGenClient(Secrets(image_gen_provider="gemini", gemini_api_key=""), mock=False)
    with pytest.raises(FatalError, match="GEMINI_API_KEY"):
        client.generate("a stickman", tmp_path / "image.png")


def test_unset_gemini_key_does_not_fall_back_to_openai_key(tmp_path: Path):
    # A stray IMAGE_GEN_API_KEY (for the openai provider) must not be
    # mistaken for a Gemini key when the provider is switched to gemini.
    client = ImageGenClient(
        Secrets(image_gen_provider="gemini", image_gen_api_key="sk-openai-leftover", gemini_api_key=""),
        mock=False,
    )
    with pytest.raises(FatalError, match="GEMINI_API_KEY"):
        client.generate("a stickman", tmp_path / "image.png")


class _FakeResponse:
    def __init__(self, status_code: int, json_body: dict):
        self.status_code = status_code
        self._json_body = json_body
        self.text = str(json_body)

    def json(self):
        return self._json_body


def test_gemini_request_shape_and_response_parsing(tmp_path: Path, monkeypatch):
    """Verifies the actual request Gemini expects (contents/parts,
    generationConfig, key as a query param) and that a well-formed
    response's inline image data gets decoded and written correctly —
    without needing a live API key."""
    captured = {}
    fake_image_bytes = b"\x89PNG\r\n\x1a\nFAKEIMAGEDATA"

    def fake_post(url, params=None, json=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["json"] = json
        return _FakeResponse(
            200,
            {
                "candidates": [
                    {"content": {"parts": [{"inlineData": {"mimeType": "image/png", "data": base64.b64encode(fake_image_bytes).decode()}}]}}
                ]
            },
        )

    monkeypatch.setattr(igc_module.requests, "post", fake_post)

    reference = tmp_path / "reference.png"
    reference.write_bytes(b"\x89PNG\r\n\x1a\nREFERENCE")
    out_path = tmp_path / "scene_001" / "image.png"

    secrets = Secrets(image_gen_provider="gemini", gemini_api_key="test-key")
    client = ImageGenClient(secrets, mock=False)
    client.generate("a stickman waving", out_path, reference_image=reference)

    assert captured["url"] == igc_module.gemini_generate_url(secrets.gemini_image_model)
    assert captured["params"] == {"key": "test-key"}
    parts = captured["json"]["contents"][0]["parts"]
    assert parts[0] == {"text": "a stickman waving"}
    assert parts[1]["inlineData"]["mimeType"] == "image/png"
    assert base64.b64decode(parts[1]["inlineData"]["data"]) == b"\x89PNG\r\n\x1a\nREFERENCE"
    assert captured["json"]["generationConfig"]["responseModalities"] == ["TEXT", "IMAGE"]

    assert out_path.read_bytes() == fake_image_bytes


def test_gemini_response_with_no_image_raises_fatal(tmp_path: Path, monkeypatch):
    def fake_post(url, params=None, json=None, timeout=None):
        return _FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": "sorry, I can't do that"}]}}]})

    monkeypatch.setattr(igc_module.requests, "post", fake_post)
    client = ImageGenClient(Secrets(image_gen_provider="gemini", gemini_api_key="test-key"), mock=False)
    with pytest.raises(FatalError, match="no image data"):
        client.generate("a stickman", tmp_path / "image.png")


def test_gemini_image_model_is_configurable(tmp_path: Path, monkeypatch):
    """Real production failure: Gemini's default image-gen model ID 404s
    once Google renames/deprecates it. GEMINI_IMAGE_MODEL must actually
    change which URL gets called, not just exist as an unused field."""
    captured = {}

    def fake_post(url, params=None, json=None, timeout=None):
        captured["url"] = url
        return _FakeResponse(200, {"candidates": [{"content": {"parts": [{"text": "no image"}]}}]})

    monkeypatch.setattr(igc_module.requests, "post", fake_post)
    client = ImageGenClient(
        Secrets(image_gen_provider="gemini", gemini_api_key="test-key", gemini_image_model="some-other-model"),
        mock=False,
    )
    with pytest.raises(FatalError):
        client.generate("a stickman", tmp_path / "image.png")

    assert captured["url"] == "https://generativelanguage.googleapis.com/v1beta/models/some-other-model:generateContent"


def test_gemini_404_gives_actionable_model_not_found_message(tmp_path: Path, monkeypatch):
    def fake_post(url, params=None, json=None, timeout=None):
        return _FakeResponse(
            404,
            {"error": {"code": 404, "message": "models/x is not found for API version v1beta", "status": "NOT_FOUND"}},
        )

    monkeypatch.setattr(igc_module.requests, "post", fake_post)
    client = ImageGenClient(
        Secrets(image_gen_provider="gemini", gemini_api_key="test-key", gemini_image_model="stale-model"),
        mock=False,
    )
    with pytest.raises(FatalError, match="GEMINI_IMAGE_MODEL") as exc_info:
        client.generate("a stickman", tmp_path / "image.png")
    assert "stale-model" in str(exc_info.value)
