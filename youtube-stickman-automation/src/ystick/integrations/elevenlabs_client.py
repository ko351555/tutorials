"""Stage 3: narration via ElevenLabs REST API (real, documented, key-based
— no browser automation needed)."""
from __future__ import annotations

from pathlib import Path

import requests

from ystick.config import Secrets
from ystick.core.exceptions import FatalError, RetryableError
from ystick.utils.http_errors import is_quota_exhausted

TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"


class ElevenLabsClient:
    def __init__(self, secrets: Secrets, mock: bool = False):
        self.secrets = secrets
        self.mock = mock

    def synthesize(self, text: str, out_path: Path, voice_id: str | None = None) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if self.mock:
            out_path.write_bytes(b"MOCK_MP3_PLACEHOLDER")
            return out_path

        voice_id = voice_id or self.secrets.elevenlabs_voice_id
        if not self.secrets.elevenlabs_api_key or not voice_id:
            raise FatalError("ELEVENLABS_API_KEY / ELEVENLABS_VOICE_ID not set")

        try:
            resp = requests.post(
                TTS_URL.format(voice_id=voice_id),
                headers={
                    "xi-api-key": self.secrets.elevenlabs_api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "text": text,
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
                },
                timeout=180,
            )
        except requests.RequestException as exc:
            raise RetryableError(f"ElevenLabs request failed: {exc}") from exc

        if is_quota_exhausted(resp.status_code, resp.text):
            raise FatalError(f"ElevenLabs out of credits/quota — check your plan: {resp.text[:500]}")
        if resp.status_code >= 500 or resp.status_code == 429:
            raise RetryableError(f"ElevenLabs {resp.status_code}: {resp.text[:500]}")
        if resp.status_code >= 400:
            raise FatalError(f"ElevenLabs {resp.status_code}: {resp.text[:500]}")

        out_path.write_bytes(resp.content)
        return out_path

    def synthesize_chunked(self, chunks: list[str], out_dir: Path, voice_id: str | None = None) -> list[Path]:
        paths = []
        for i, chunk in enumerate(chunks):
            path = out_dir / f"chunk_{i:03d}.mp3"
            self.synthesize(chunk, path, voice_id=voice_id)
            paths.append(path)
        return paths
