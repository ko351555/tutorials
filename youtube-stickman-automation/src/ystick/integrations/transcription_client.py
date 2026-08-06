"""Stage 4: word + sentence timestamps from the narration audio.

FoziScribe AI has no confirmed public API as of this writing, so this module
defines one interface with two implementations behind it (see
docs/ARCHITECTURE.md §6) — swap providers via
config/settings.yaml -> stages.timestamps.provider / TRANSCRIPTION_PROVIDER
with zero changes to stage code.
"""
from __future__ import annotations

import re
from abc import ABC, abstractmethod
from pathlib import Path

from ystick.config import Secrets
from ystick.core.exceptions import FatalError, RetryableError

FOZISCRIBE_UPLOAD_URL = "https://api.fozi-scribe.example/v1/transcriptions"  # TODO: confirm real endpoint


class TranscriptionClient(ABC):
    @abstractmethod
    def transcribe(self, audio_path: Path) -> dict:
        """Returns {"text": str, "words": [{"word","start_ms","end_ms"}...],
        "sentences": [{"text","start_ms","end_ms"}...]}"""
        raise NotImplementedError


class FoziScribeClient(TranscriptionClient):
    """REST client stub — fill in once FoziScribe publishes API docs or you
    obtain an API key. Until then, prefer WhisperLocalClient (below) as the
    reliable default; both implement the same interface so switching back
    is a one-line config change."""

    def __init__(self, secrets: Secrets):
        self.secrets = secrets

    def transcribe(self, audio_path: Path) -> dict:
        if not self.secrets.fozi_scribe_api_key:
            raise FatalError(
                "FOZISCRIBE_API_KEY not set. FoziScribe has no confirmed public API — "
                "either supply the key + confirm the endpoint in transcription_client.py, "
                "or set TRANSCRIPTION_PROVIDER=whisper_local in .env for a working default."
            )
        raise FatalError(
            "FoziScribeClient is a stub pending confirmed API docs — see the TODO in "
            "transcription_client.py. Use TRANSCRIPTION_PROVIDER=whisper_local for now."
        )


class WhisperLocalClient(TranscriptionClient):
    """Local, zero-account fallback using faster-whisper. Works today with
    no API key at all — the recommended default until/unless FoziScribe's
    API is confirmed."""

    def transcribe(self, audio_path: Path) -> dict:
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise FatalError(
                "faster-whisper not installed — run `pip install -e '.[whisper]'`"
            ) from exc

        try:
            model = WhisperModel("base", device="cpu", compute_type="int8")
            segments, _info = model.transcribe(str(audio_path), word_timestamps=True)
        except Exception as exc:  # noqa: BLE001
            raise RetryableError(f"whisper transcription failed: {exc}") from exc

        words, sentences, full_text = [], [], []
        for seg in segments:
            sentences.append(
                {"text": seg.text.strip(), "start_ms": int(seg.start * 1000), "end_ms": int(seg.end * 1000)}
            )
            full_text.append(seg.text.strip())
            for w in seg.words or []:
                words.append({"word": w.word.strip(), "start_ms": int(w.start * 1000), "end_ms": int(w.end * 1000)})

        return {"text": " ".join(full_text), "words": words, "sentences": sentences}


class MockTranscriptionClient(TranscriptionClient):
    """Evenly-spaced fake timestamps derived straight from the script text,
    so downstream stages (scene planning, subtitles) have realistic-shaped
    input with zero cost/dependencies."""

    def __init__(self, script_text: str, wpm: int = 150):
        self.script_text = script_text
        self.wpm = wpm

    def transcribe(self, audio_path: Path) -> dict:
        sentences_raw = [s.strip() for s in re.split(r"(?<=[.!?])\s+", self.script_text) if s.strip()]
        ms_per_word = 60_000 / self.wpm
        t = 0
        words, sentences = [], []
        for sentence in sentences_raw:
            sent_start = t
            for word in sentence.split():
                start = t
                end = t + ms_per_word
                words.append({"word": word, "start_ms": int(start), "end_ms": int(end)})
                t = end
            sentences.append({"text": sentence, "start_ms": int(sent_start), "end_ms": int(t)})
        return {"text": self.script_text, "words": words, "sentences": sentences}


def build_transcription_client(secrets: Secrets, mock: bool, script_text: str = "") -> TranscriptionClient:
    if mock:
        return MockTranscriptionClient(script_text)
    provider = secrets.transcription_provider
    if provider == "fozi_scribe":
        return FoziScribeClient(secrets)
    if provider == "whisper_local":
        return WhisperLocalClient()
    raise FatalError(f"unknown TRANSCRIPTION_PROVIDER: {provider!r}")
