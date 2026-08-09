"""One-time OAuth authorization + resumable upload to YouTube via the
YouTube Data API v3.

First-time setup (do this once):
  1. Go to https://console.cloud.google.com/ and create a project.
  2. Enable the "YouTube Data API v3" for that project.
  3. Create OAuth 2.0 credentials of type "Desktop app" and download the
     JSON — save it as `client_secrets.json` in this directory (never commit it).
  4. Run any command in this pipeline once (e.g. `python youtube_upload.py --help`
     doesn't trigger auth; the first real upload will). A browser window opens,
     you sign in with the Google account that owns the DreamSanctumMusic
     channel and approve access. A `token.json` is cached afterwards so every
     future run is fully unattended (no browser) until the refresh token is
     revoked.

client_secrets.json and token.json both grant upload access to the channel —
keep them out of git (already covered by this project's .gitignore).
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Callable

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

DEFAULT_CLIENT_SECRETS = Path(__file__).parent.parent / "client_secrets.json"
DEFAULT_TOKEN_PATH = Path(__file__).parent.parent / "token.json"

# https://developers.google.com/youtube/v3/docs/videoCategories/list
CATEGORY_MUSIC = "10"


def get_authenticated_service(
    client_secrets_path: str | Path = DEFAULT_CLIENT_SECRETS,
    token_path: str | Path = DEFAULT_TOKEN_PATH,
):
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    client_secrets_path = Path(client_secrets_path)
    token_path = Path(token_path)

    if not client_secrets_path.exists():
        raise FileNotFoundError(
            f"{client_secrets_path} not found. Follow the setup steps in this file's "
            "docstring to download OAuth credentials from Google Cloud Console."
        )

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("youtube", "v3", credentials=creds)


def upload_video(
    file_path: str | Path,
    title: str,
    description: str,
    tags: list[str] | None = None,
    category_id: str = CATEGORY_MUSIC,
    privacy_status: str = "private",
    publish_at: str | None = None,
    made_for_kids: bool = False,
    thumbnail_path: str | Path | None = None,
    client_secrets_path: str | Path = DEFAULT_CLIENT_SECRETS,
    token_path: str | Path = DEFAULT_TOKEN_PATH,
    on_log: Callable[[str], None] | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> str:
    """Upload a video and return its YouTube video ID.

    `publish_at` (RFC3339, e.g. "2026-08-15T09:00:00Z") schedules the video —
    YouTube requires privacy_status to be "private" when publish_at is set;
    it flips to public automatically at that time.

    `on_log`/`on_progress` mirror assemble.assemble()'s callbacks, for a UI
    to show upload progress separately from the ffmpeg assembly progress.
    """
    from googleapiclient.http import MediaFileUpload
    from googleapiclient.errors import HttpError

    log = on_log or print
    youtube = get_authenticated_service(client_secrets_path, token_path)

    status = {
        "privacyStatus": "private" if publish_at else privacy_status,
        "selfDeclaredMadeForKids": made_for_kids,
    }
    if publish_at:
        status["publishAt"] = publish_at

    body = {
        "snippet": {
            "title": title[:100],
            "description": description[:5000],
            "tags": (tags or [])[:500],
            "categoryId": category_id,
        },
        "status": status,
    }

    media = MediaFileUpload(str(file_path), chunksize=50 * 1024 * 1024, resumable=True)
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)

    log(f"Uploading {file_path} ...")
    response = None
    while response is None:
        try:
            status_obj, response = request.next_chunk()
            if status_obj:
                pct = status_obj.progress() * 100
                if on_progress:
                    on_progress(pct)
                log(f"  {int(pct)}% uploaded")
        except HttpError as e:
            if e.resp.status in (500, 502, 503, 504):
                log(f"  Transient error {e.resp.status}, retrying chunk...")
                continue
            raise

    video_id = response["id"]
    if on_progress:
        on_progress(100.0)
    log(f"Uploaded: https://youtu.be/{video_id}")

    if thumbnail_path:
        youtube.thumbnails().set(videoId=video_id, media_body=MediaFileUpload(str(thumbnail_path))).execute()
        log(f"  Thumbnail set from {thumbnail_path}")

    return video_id


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--file", required=True, help="Path to the final MP4")
    ap.add_argument("--title", required=True)
    ap.add_argument("--description", required=True)
    ap.add_argument("--tags", default="", help="Comma-separated tags")
    ap.add_argument("--category-id", default=CATEGORY_MUSIC)
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    ap.add_argument("--publish-at", default=None, help="RFC3339 timestamp to schedule, e.g. 2026-08-15T09:00:00Z")
    ap.add_argument("--made-for-kids", action="store_true")
    ap.add_argument("--thumbnail", default=None)
    ap.add_argument("--client-secrets", default=str(DEFAULT_CLIENT_SECRETS))
    ap.add_argument("--token", default=str(DEFAULT_TOKEN_PATH))
    args = ap.parse_args()

    tags = [t.strip() for t in args.tags.split(",") if t.strip()]

    upload_video(
        file_path=args.file,
        title=args.title,
        description=args.description,
        tags=tags,
        category_id=args.category_id,
        privacy_status=args.privacy,
        publish_at=args.publish_at,
        made_for_kids=args.made_for_kids,
        thumbnail_path=args.thumbnail,
        client_secrets_path=args.client_secrets,
        token_path=args.token,
    )


if __name__ == "__main__":
    main()
