"""Stage 9: branding via Canva Connect (Autofill + Export APIs).

Canva's Autofill API populates a pre-built Brand Template's named fields
(text/logo/image placeholders) and Export renders that template to a file —
it does not ingest an arbitrary externally-produced narrated video. So the
realistic flow is: export the branded intro/outro as short clips from the
template, then splice them around the rough cut with FFmpeg. Build the
Brand Template once in Canva's editor with named fields, record its
template_id in .env, and this becomes a fully automated step.

Canva Connect apps use OAuth2 with PKCE and no client-side redirect
listener is assumed — run `ystick canva-auth` once (see
core/canva_oauth_setup.py) to mint a long-lived CANVA_REFRESH_TOKEN via a
paste-back flow, then this client silently exchanges it for a fresh
short-lived access token on every call.
"""
from __future__ import annotations

import shutil
import time
from pathlib import Path

import requests
import structlog

from ystick.config import Secrets
from ystick.core.exceptions import FatalError, RetryableError
from ystick.integrations.video_assembly import run_ffmpeg

log = structlog.get_logger()

AUTOFILL_URL = "https://api.canva.com/rest/v1/autofills"
EXPORT_URL = "https://api.canva.com/rest/v1/exports"
TOKEN_URL = "https://api.canva.com/rest/v1/oauth/token"
AUTHORIZATION_URL = "https://www.canva.com/api/oauth/authorize"


class CanvaClient:
    def __init__(self, secrets: Secrets, mock: bool = False):
        self.secrets = secrets
        self.mock = mock

    def _configured(self, template_id: str) -> bool:
        return bool(template_id and self.secrets.canva_client_id and self.secrets.canva_client_secret)

    def _access_token(self) -> str:
        if not self.secrets.canva_refresh_token:
            raise FatalError(
                "Canva not authorized yet — run `ystick canva-auth` once (needs "
                "CANVA_CLIENT_ID/CANVA_CLIENT_SECRET already set in .env) to mint "
                "a CANVA_REFRESH_TOKEN, then add it to .env."
            )
        try:
            resp = requests.post(
                TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": self.secrets.canva_refresh_token,
                    "client_id": self.secrets.canva_client_id,
                    "client_secret": self.secrets.canva_client_secret,
                },
                timeout=30,
            )
        except requests.RequestException as exc:
            raise RetryableError(f"Canva token refresh failed: {exc}") from exc
        if resp.status_code >= 500:
            raise RetryableError(f"Canva token refresh {resp.status_code}")
        if resp.status_code >= 400:
            raise FatalError(
                f"Canva token refresh {resp.status_code} — CANVA_REFRESH_TOKEN may be "
                f"revoked or expired; re-run `ystick canva-auth`: {resp.text[:500]}"
            )
        body = resp.json()
        new_refresh_token = body.get("refresh_token")
        if new_refresh_token and new_refresh_token != self.secrets.canva_refresh_token:
            # Some OAuth providers rotate the refresh token on every use.
            # Don't silently rewrite .env — surface it so the human updates
            # it (the old one may already be invalid after this call).
            log.warning(
                "canva.refresh_token_rotated",
                detail="Canva issued a new refresh token — update CANVA_REFRESH_TOKEN "
                f"in .env to: {new_refresh_token}",
            )
        return body["access_token"]

    def _export_template_clip(self, template_id: str, fields: dict, out_path: Path) -> Path:
        token = self._access_token()
        try:
            autofill_resp = requests.post(
                AUTOFILL_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={"brand_template_id": template_id, "data": fields},
                timeout=60,
            )
        except requests.RequestException as exc:
            raise RetryableError(f"Canva autofill request failed: {exc}") from exc
        if autofill_resp.status_code >= 500:
            raise RetryableError(f"Canva autofill {autofill_resp.status_code}")
        if autofill_resp.status_code >= 400:
            raise FatalError(f"Canva autofill {autofill_resp.status_code}: {autofill_resp.text[:500]}")

        design_id = autofill_resp.json()["design"]["id"]
        export_resp = requests.post(
            EXPORT_URL,
            headers={"Authorization": f"Bearer {token}"},
            json={"design_id": design_id, "format": {"type": "mp4"}},
            timeout=60,
        )
        job_id = export_resp.json()["job"]["id"]
        # Poll for export completion (Canva exports are async).
        for _ in range(30):
            status = requests.get(f"{EXPORT_URL}/{job_id}", headers={"Authorization": f"Bearer {token}"}).json()
            if status["job"]["status"] == "success":
                url = status["job"]["urls"][0]
                out_path.write_bytes(requests.get(url, timeout=120).content)
                return out_path
            if status["job"]["status"] == "failed":
                raise FatalError(f"Canva export failed: {status}")
            time.sleep(2)
        raise RetryableError("Canva export timed out waiting for job completion")

    def apply_branding(self, rough_cut: Path, out_path: Path, fields: dict, *, template_id: str) -> Path:
        """template_id must match rough_cut's own dimensions — Canva Brand
        Templates render at whatever canvas size they were built with, so
        the long-form (16:9) and Shorts (9:16) templates are two separate
        Canva templates, never the same one."""
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if self.mock:
            shutil.copyfile(rough_cut, out_path)
            return out_path

        if not self._configured(template_id):
            # Canva Connect requires a one-time OAuth2/PKCE app setup plus a
            # hand-built Brand Template — most channels won't have that
            # wired up yet. Branding is an enhancement (intro/outro), not
            # the deliverable, so pass the video through unbranded rather
            # than blocking the whole pipeline on it.
            log.warning(
                "branding.canva_not_configured",
                detail="CANVA_CLIENT_ID/CANVA_CLIENT_SECRET/a brand template_id "
                "not fully set — skipping Canva branding, passing the video "
                "through unbranded. See .env.example for setup.",
            )
            shutil.copyfile(rough_cut, out_path)
            return out_path

        clips_dir = out_path.parent / "canva_clips"
        clips_dir.mkdir(exist_ok=True)
        # Reuse the same "title" data field for both exports, but with
        # different content, so intro and outro actually look different
        # from one template — the video's title on the intro card, a CTA
        # on the outro card — rather than autofilling identical data twice.
        cta_text = fields.get("cta_text") or f"Subscribe to {fields.get('channel_name', 'the channel')} for more!"
        intro_fields = {**fields, "segment": "intro"}
        outro_fields = {**fields, "title": cta_text, "segment": "outro"}
        intro = self._export_template_clip(template_id, intro_fields, clips_dir / "intro.mp4")
        outro = self._export_template_clip(template_id, outro_fields, clips_dir / "outro.mp4")

        concat_list = clips_dir / "concat_list.txt"
        concat_list.write_text(
            "\n".join(f"file '{p.resolve()}'" for p in [intro, rough_cut, outro])
        )
        run_ffmpeg([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
            "-c:v", "libx264", "-c:a", "aac", str(out_path),
        ])
        return out_path
