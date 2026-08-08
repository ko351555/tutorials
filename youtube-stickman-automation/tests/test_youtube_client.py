from pathlib import Path

from ystick.config import Secrets
from ystick.integrations.youtube_client import YouTubeClient


def test_create_draft_skips_gracefully_when_not_configured(tmp_path: Path):
    """Real production case: no YouTube OAuth app / refresh token set up
    yet. The video and drafted metadata are the deliverable — the upload
    should skip, not block the pipeline."""
    video_path = tmp_path / "final.mp4"
    video_path.write_bytes(b"FAKE_VIDEO_BYTES")

    client = YouTubeClient(Secrets(), mock=False)
    result = client.create_draft(video_path, {"title": "t", "description": "d", "tags": []})

    assert result == {"video_id": None, "status": "skipped_not_configured"}


def test_create_draft_mock_mode():
    client = YouTubeClient(Secrets(), mock=True)
    result = client.create_draft(Path("unused.mp4"), {"title": "t", "description": "d", "tags": []})
    assert result == {"video_id": "MOCK_VIDEO_ID", "status": "mock"}


def test_configured_requires_all_three_credentials():
    assert not YouTubeClient(Secrets())._configured()
    assert not YouTubeClient(Secrets(youtube_oauth_client_id="id"))._configured()
    assert YouTubeClient(
        Secrets(
            youtube_oauth_client_id="id",
            youtube_oauth_client_secret="secret",
            youtube_oauth_refresh_token="token",
        )
    )._configured()
