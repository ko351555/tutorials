"""Stage 9: branding via Canva Connect (Autofill + Export APIs).

Canva's Autofill API populates a pre-built Brand Template's named fields
(text/logo/image placeholders) and Export renders that template to a file —
it does not ingest an arbitrary externally-produced narrated video. So the
realistic flow is: export the branded intro/outro as short clips from the
template, then splice them around the rough cut with FFmpeg. Build the
Brand Template once in Canva's editor with named fields, record its
template_id in .env, and this becomes a fully automated step.

Requires a one-time OAuth setup (Canva Connect apps use OAuth2 with PKCE);
this client assumes an already-obtained access token is available via
secrets — wire up the OAuth exchange in your deployment before going live.
"""
from __future__ import annotations

import shutil
import subprocess
import time
from pathlib import Path

import requests
import structlog

from ystick.config import Secrets
from ystick.core.exceptions import FatalError, RetryableError

log = structlog.get_logger()

AUTOFILL_URL = "https://api.canva.com/rest/v1/autofills"
EXPORT_URL = "https://api.canva.com/rest/v1/exports"


class CanvaClient:
    def __init__(self, secrets: Secrets, mock: bool = False):
        self.secrets = secrets
        self.mock = mock

    def _configured(self) -> bool:
        return bool(
            self.secrets.canva_brand_template_id
            and self.secrets.canva_client_id
            and self.secrets.canva_client_secret
        )

    def _access_token(self) -> str:
        # TODO: implement the OAuth2 (PKCE) exchange/refresh for Canva
        # Connect and cache the token; client_id/secret are already read
        # from .env via Secrets.
        raise FatalError(
            "Canva OAuth access token not configured — implement the OAuth "
            "exchange in canva_client.py._access_token() before going live."
        )

    def _export_template_clip(self, fields: dict, out_path: Path) -> Path:
        if not self.secrets.canva_brand_template_id:
            raise FatalError("CANVA_BRAND_TEMPLATE_ID not set")
        token = self._access_token()
        try:
            autofill_resp = requests.post(
                AUTOFILL_URL,
                headers={"Authorization": f"Bearer {token}"},
                json={"brand_template_id": self.secrets.canva_brand_template_id, "data": fields},
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

    def apply_branding(self, rough_cut: Path, out_path: Path, fields: dict) -> Path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        if self.mock:
            shutil.copyfile(rough_cut, out_path)
            return out_path

        if not self._configured():
            # Canva Connect requires a one-time OAuth2/PKCE app setup plus a
            # hand-built Brand Template — most channels won't have that
            # wired up yet. Branding is an enhancement (intro/outro), not
            # the deliverable, so pass the rough cut through unbranded
            # rather than blocking the whole pipeline on it.
            log.warning(
                "branding.canva_not_configured",
                detail="CANVA_CLIENT_ID/CANVA_CLIENT_SECRET/CANVA_BRAND_TEMPLATE_ID "
                "not fully set — skipping Canva branding, passing the rough cut "
                "through unbranded. See .env.example for setup.",
            )
            shutil.copyfile(rough_cut, out_path)
            return out_path

        clips_dir = out_path.parent / "canva_clips"
        clips_dir.mkdir(exist_ok=True)
        intro = self._export_template_clip({**fields, "segment": "intro"}, clips_dir / "intro.mp4")
        outro = self._export_template_clip({**fields, "segment": "outro"}, clips_dir / "outro.mp4")

        concat_list = clips_dir / "concat_list.txt"
        concat_list.write_text(
            "\n".join(f"file '{p.resolve()}'" for p in [intro, rough_cut, outro])
        )
        subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list),
             "-c:v", "libx264", "-c:a", "aac", str(out_path)],
            check=True, capture_output=True,
        )
        return out_path
