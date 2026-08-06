"""Stage 10: draft the video on YouTube (private/unlisted) with full
metadata via the YouTube Data API v3. The pipeline never auto-publishes —
a human always clicks Publish in Studio. Community posts have no public
API and are left as pre-drafted copy for manual posting.

For production use, prefer `google-api-python-client` + its resumable
upload helpers over raw requests; this client shows the shape of the calls
needed (OAuth2 bearer token from a refresh token) without pulling in that
dependency for a scaffold that may never touch the live API during
development.
"""
from __future__ import annotations

from pathlib import Path

import requests

from ystick.config import Secrets
from ystick.core.exceptions import FatalError, RetryableError

TOKEN_URL = "https://oauth2.googleapis.com/token"
UPLOAD_URL = "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status"


class YouTubeClient:
    def __init__(self, secrets: Secrets, mock: bool = False):
        self.secrets = secrets
        self.mock = mock

    def _access_token(self) -> str:
        creds = self.secrets
        if not all([creds.youtube_oauth_client_id, creds.youtube_oauth_client_secret, creds.youtube_oauth_refresh_token]):
            raise FatalError("YOUTUBE_OAUTH_* not fully set in .env")
        try:
            resp = requests.post(
                TOKEN_URL,
                data={
                    "client_id": creds.youtube_oauth_client_id,
                    "client_secret": creds.youtube_oauth_client_secret,
                    "refresh_token": creds.youtube_oauth_refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=30,
            )
        except requests.RequestException as exc:
            raise RetryableError(f"YouTube token refresh failed: {exc}") from exc
        if resp.status_code >= 400:
            raise FatalError(f"YouTube token refresh {resp.status_code}: {resp.text[:500]}")
        return resp.json()["access_token"]

    def create_draft(self, video_path: Path, metadata: dict, privacy: str = "private") -> dict:
        """metadata: {"title","description","tags","chapters"(-> folded into
        description)}. Returns {"video_id": str} or a mock stand-in."""
        if self.mock:
            return {"video_id": "MOCK_VIDEO_ID", "status": "mock"}

        token = self._access_token()
        body = {
            "snippet": {
                "title": metadata["title"],
                "description": metadata["description"],
                "tags": metadata.get("tags", []),
            },
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False},
        }
        try:
            init_resp = requests.post(
                UPLOAD_URL,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                json=body,
                timeout=60,
            )
        except requests.RequestException as exc:
            raise RetryableError(f"YouTube upload init failed: {exc}") from exc
        if init_resp.status_code >= 500:
            raise RetryableError(f"YouTube upload init {init_resp.status_code}")
        if init_resp.status_code >= 400:
            raise FatalError(f"YouTube upload init {init_resp.status_code}: {init_resp.text[:500]}")

        upload_session_url = init_resp.headers["Location"]
        with open(video_path, "rb") as f:
            put_resp = requests.put(upload_session_url, data=f, timeout=1800)
        if put_resp.status_code >= 400:
            raise RetryableError(f"YouTube video upload {put_resp.status_code}: {put_resp.text[:500]}")
        return {"video_id": put_resp.json()["id"], "status": "uploaded_draft"}
