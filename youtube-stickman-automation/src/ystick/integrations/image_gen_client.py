"""Stage 7: turn each scene's prompt into an image, holding style/character
consistency via a reference image passed on every call.

Two API providers (plus "manual", handled entirely in
stages/stage7_image_generation.py, which never touches this client):
- openai (default): OpenAI Images API. Needs its own billing, separate
  from a ChatGPT Pro chat subscription.
- gemini: Google's Gemini API (get a key at aistudio.google.com). Gemini's
  multimodal `generateContent` endpoint doubles as an image generator when
  given an image-capable model, and accepts a reference image as another
  input part for the same consistency-locking purpose as OpenAI's edits
  endpoint. Gemini's free tier covers text generation generously, but
  image-output models have been observed with a hard zero free-tier quota
  (confirmed live: 429 "limit: 0") — in practice this needs billing
  enabled on the Google Cloud project behind the API key, same as OpenAI.

Google Flow and Canva's Magic Media are UI-only (see docs/ARCHITECTURE.md
§6) so they aren't wired in here at all — Flow is built on the same
Imagen family of models Gemini exposes via API, which is the point of the
gemini provider.
"""
from __future__ import annotations

import base64
from pathlib import Path

import requests

from ystick.config import Secrets
from ystick.core.exceptions import FatalError, RetryableError
from ystick.utils.http_errors import is_quota_exhausted

OPENAI_IMAGES_URL = "https://api.openai.com/v1/images/generations"
OPENAI_IMAGE_EDITS_URL = "https://api.openai.com/v1/images/edits"

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"


def gemini_generate_url(model: str) -> str:
    return f"{GEMINI_API_BASE}/models/{model}:generateContent"

_MIME_BY_SUFFIX = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}

# 1x1 transparent PNG — used only as a mock placeholder so mock-mode output
# is a byte-valid (if meaningless) image file rather than garbage bytes.
_MOCK_PNG_BYTES = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class ImageGenClient:
    def __init__(self, secrets: Secrets, mock: bool = False):
        self.secrets = secrets
        self.mock = mock

    def generate(self, prompt: str, out_path: Path, reference_image: Path | None = None) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if self.mock:
            out_path.write_bytes(_MOCK_PNG_BYTES)
            return out_path

        if self.secrets.image_gen_provider == "gemini":
            return self._generate_gemini(prompt, out_path, reference_image)
        return self._generate_openai(prompt, out_path, reference_image)

    # -- OpenAI --------------------------------------------------------------

    def _generate_openai(self, prompt: str, out_path: Path, reference_image: Path | None) -> Path:
        if not self.secrets.image_gen_api_key:
            raise FatalError("IMAGE_GEN_API_KEY not set")

        headers = {"Authorization": f"Bearer {self.secrets.image_gen_api_key}"}
        try:
            if reference_image and reference_image.exists():
                # Reference-conditioned edit call — keeps character/style locked
                # to the prior scene's (or the canonical) reference image.
                with open(reference_image, "rb") as ref_f:
                    resp = requests.post(
                        OPENAI_IMAGE_EDITS_URL,
                        headers=headers,
                        files={"image": ref_f},
                        data={"prompt": prompt, "model": "gpt-image-1", "size": "1024x1024"},
                        timeout=180,
                    )
            else:
                resp = requests.post(
                    OPENAI_IMAGES_URL,
                    headers=headers,
                    json={"prompt": prompt, "model": "gpt-image-1", "size": "1024x1024"},
                    timeout=180,
                )
        except requests.RequestException as exc:
            raise RetryableError(f"image gen request failed: {exc}") from exc

        if is_quota_exhausted(resp.status_code, resp.text):
            raise FatalError(
                f"image gen out of credits/quota — add billing at "
                f"platform.openai.com before retrying: {resp.text[:500]}"
            )
        if resp.status_code >= 500 or resp.status_code == 429:
            raise RetryableError(f"image gen {resp.status_code}: {resp.text[:500]}")
        if resp.status_code >= 400:
            raise FatalError(f"image gen {resp.status_code}: {resp.text[:500]}")

        b64 = resp.json()["data"][0]["b64_json"]
        out_path.write_bytes(base64.b64decode(b64))
        return out_path

    # -- Gemini ----------------------------------------------------------------

    def _generate_gemini(self, prompt: str, out_path: Path, reference_image: Path | None) -> Path:
        if not self.secrets.gemini_api_key:
            raise FatalError("GEMINI_API_KEY not set — get a free key at aistudio.google.com")

        parts: list[dict] = [{"text": prompt}]
        if reference_image and reference_image.exists():
            mime_type = _MIME_BY_SUFFIX.get(reference_image.suffix.lower(), "image/png")
            b64_ref = base64.b64encode(reference_image.read_bytes()).decode("ascii")
            parts.append({"inlineData": {"mimeType": mime_type, "data": b64_ref}})

        body = {
            "contents": [{"parts": parts}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
        }
        model = self.secrets.gemini_image_model
        try:
            resp = requests.post(
                gemini_generate_url(model),
                params={"key": self.secrets.gemini_api_key},
                json=body,
                timeout=180,
            )
        except requests.RequestException as exc:
            raise RetryableError(f"Gemini request failed: {exc}") from exc

        if resp.status_code == 404:
            # Google renames/deprecates image-gen model IDs fairly often —
            # this is near-certainly a stale GEMINI_IMAGE_MODEL, not a
            # transient issue, so fail fast with the fix instead of
            # retrying a request that will 404 every time.
            raise FatalError(
                f"Gemini model '{model}' not found/not supported for image generation "
                f"(likely renamed or deprecated by Google). Fix: list your available "
                f"models at https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY "
                f"(or see https://ai.google.dev/gemini-api/docs/image-generation), then set "
                f"GEMINI_IMAGE_MODEL=<current model id> in .env. Raw response: {resp.text[:500]}"
            )
        if resp.status_code == 429 and "limit: 0" in resp.text:
            # A per-minute/per-day rate limit is transient and worth
            # retrying — "limit: 0" is not. It means this model has zero
            # free-tier quota at all (image-output models commonly require
            # billing enabled, unlike Gemini's free text-only tier), so
            # every retry will 429 identically. Fail fast with the fix.
            #
            # Confirmed in the wild: having a funded Cloud Billing account
            # is NOT sufficient by itself — aistudio.google.com/apikey also
            # has a separate per-project "Free tier" -> "Paid tier" toggle
            # that must be switched explicitly, and it can take a while to
            # propagate. A funded billing account with the key still on
            # "Free tier" reproduces this exact zero-quota 429.
            raise FatalError(
                f"Gemini model '{model}' has zero free-tier quota for your project — "
                f"image generation on Gemini typically requires billing enabled (unlike "
                f"Gemini's free text-only tier). A funded Cloud Billing account alone is "
                f"NOT enough: go to https://aistudio.google.com/apikey, find this key's "
                f"project, and confirm it's switched to 'Paid tier' (not just that billing "
                f"is attached) — this is a separate toggle. If it's already on Paid tier, "
                f"the switch can take time to propagate; otherwise switch IMAGE_GEN_PROVIDER "
                f"to manual (no cost) or openai (separate billing) in .env. "
                f"Raw response: {resp.text[:500]}"
            )
        if resp.status_code >= 500 or resp.status_code == 429:
            raise RetryableError(f"Gemini {resp.status_code}: {resp.text[:500]}")
        if resp.status_code >= 400:
            raise FatalError(f"Gemini {resp.status_code}: {resp.text[:500]}")

        data = resp.json()
        try:
            response_parts = data["candidates"][0]["content"]["parts"]
        except (KeyError, IndexError) as exc:
            raise FatalError(f"Gemini response had no candidates: {str(data)[:500]}") from exc

        for part in response_parts:
            inline = part.get("inlineData")
            if inline and inline.get("data"):
                out_path.write_bytes(base64.b64decode(inline["data"]))
                return out_path

        raise FatalError(f"Gemini response contained no image data: {str(data)[:500]}")
