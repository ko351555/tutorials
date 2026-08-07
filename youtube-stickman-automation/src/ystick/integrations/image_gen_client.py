"""Stage 7: turn each scene's prompt into an image, holding style/character
consistency via a reference image passed on every call.

Google Flow and Canva's Magic Media are UI-only today (see
docs/ARCHITECTURE.md §6) so they aren't wired in here — this client targets
any reference-image-capable generation API (default: OpenAI Images API).
Swap the `provider` in .env if you use a different consistency-oriented
model; the interface (`generate(prompt, reference_image, out_path)`) stays
the same.
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
