"""Loads config/settings.yaml + .env into one Settings object.

Kept deliberately simple (attribute-access dict wrapper) rather than a
fully-typed pydantic tree, because settings.yaml is meant to be hand-edited
and extended per channel without touching this loader.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]
_ENV_VAR_RE = re.compile(r"\$\{([A-Z0-9_]+)\}")


class AttrDict(dict):
    """dict that also supports attribute access, recursively."""

    def __getattr__(self, item: str) -> Any:
        try:
            value = self[item]
        except KeyError as exc:
            raise AttributeError(item) from exc
        return _wrap(value)

    def __setattr__(self, key: str, value: Any) -> None:
        self[key] = value


def _wrap(value: Any) -> Any:
    if isinstance(value, dict) and not isinstance(value, AttrDict):
        return AttrDict(value)
    if isinstance(value, list):
        return [_wrap(v) for v in value]
    return value


def _substitute_env(value: Any) -> Any:
    if isinstance(value, str):
        def repl(match: "re.Match[str]") -> str:
            return os.environ.get(match.group(1), "")

        return _ENV_VAR_RE.sub(repl, value)
    if isinstance(value, dict):
        return {k: _substitute_env(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_substitute_env(v) for v in value]
    return value


class Secrets(BaseSettings):
    """Everything that must never appear in settings.yaml or logs."""

    model_config = SettingsConfigDict(env_file=str(PROJECT_ROOT / ".env"), extra="ignore")

    llm_provider: str = "claude_code"
    openai_api_key: str = ""

    elevenlabs_api_key: str = ""
    elevenlabs_voice_id: str = ""

    transcription_provider: str = "whisper_local"
    fozi_scribe_api_key: str = ""

    # image_gen_provider: openai | gemini | manual — see .env.example
    image_gen_provider: str = "openai"
    image_gen_api_key: str = ""
    gemini_api_key: str = ""
    # Google renames/deprecates these fairly often — if generation 404s with
    # "model ... is not found", check https://ai.google.dev/gemini-api/docs/image-generation
    # (or GET https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY
    # for the exact current names) and override here rather than waiting on
    # a code change.
    gemini_image_model: str = "gemini-2.5-flash-image"

    canva_client_id: str = ""
    canva_client_secret: str = ""
    canva_brand_template_id: str = ""
    # A SEPARATE Brand Template built at 1080x1920 (9:16) in Canva's editor
    # — Canva templates aren't dimension-agnostic, so the 16:9 template
    # above can't be reused for Shorts. Optional: Shorts ship unbranded if
    # this isn't set, same graceful-skip as the long-form template.
    canva_shorts_brand_template_id: str = ""
    # Obtained via `ystick canva-auth` (one-time interactive OAuth2/PKCE
    # consent flow) — never set by hand. Long-lived; the pipeline mints a
    # fresh short-lived access token from this on every Canva call.
    canva_refresh_token: str = ""
    # Must exactly match a Redirect URI registered on the integration at
    # canva.com/developers — canva-auth uses this as a paste-back landing
    # page, not a real listening server (see canva_client.py).
    canva_redirect_uri: str = "http://127.0.0.1:8765/callback"
    # Space-separated. Canva's exact scope catalog can shift — if
    # canva-auth's authorization step is rejected, check
    # https://www.canva.com/developers/docs/connect-api/authentication/
    # and override here to match what your integration is permitted to
    # request.
    canva_scopes: str = (
        "design:content:read design:content:write design:meta:read "
        "brandtemplate:content:read brandtemplate:meta:read asset:read asset:write"
    )

    youtube_oauth_client_id: str = ""
    youtube_oauth_client_secret: str = ""
    youtube_oauth_refresh_token: str = ""

    def redacted_summary(self) -> dict[str, str]:
        out = {}
        for key, value in self.model_dump().items():
            out[key] = "<set>" if value else "<empty>"
        return out


def load_settings(settings_path: Path | None = None) -> AttrDict:
    settings_path = settings_path or PROJECT_ROOT / "config" / "settings.yaml"
    raw = yaml.safe_load(settings_path.read_text())
    raw = _substitute_env(raw)
    settings = AttrDict(raw)
    settings["_root"] = str(PROJECT_ROOT)
    return settings


def load_secrets() -> Secrets:
    return Secrets()


def load_blueprint(settings: AttrDict | None = None) -> AttrDict:
    """The channel identity layer: who this channel is, what it covers, how
    often it posts. Distinct from settings.yaml (pipeline knobs) and the
    style/visual guides (how it sounds/looks) — this is what topic discovery
    falls back to when given no explicit idea, and what the UI shows as
    channel branding. See config/channel_blueprint.yaml."""
    settings = settings or load_settings()
    blueprint_path = PROJECT_ROOT / settings.channel.blueprint_path
    raw = yaml.safe_load(blueprint_path.read_text())
    return AttrDict(raw)
