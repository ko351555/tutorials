from pathlib import Path

from ystick.config import Secrets
from ystick.integrations.canva_client import CanvaClient


def test_apply_branding_skips_gracefully_when_not_configured(tmp_path: Path):
    """Real production case: no Canva Connect app / brand template set up
    yet. Branding is an enhancement, not the deliverable — the rough cut
    should pass through unbranded instead of blocking the pipeline."""
    rough_cut = tmp_path / "rough_cut.mp4"
    rough_cut.write_bytes(b"FAKE_VIDEO_BYTES")
    out_path = tmp_path / "09_final" / "branded_cut.mp4"

    client = CanvaClient(Secrets(), mock=False)
    result = client.apply_branding(rough_cut, out_path, {"title": "t", "channel_name": "c"})

    assert result == out_path
    assert out_path.read_bytes() == b"FAKE_VIDEO_BYTES"


def test_apply_branding_mock_mode_passes_through(tmp_path: Path):
    rough_cut = tmp_path / "rough_cut.mp4"
    rough_cut.write_bytes(b"FAKE_VIDEO_BYTES")
    out_path = tmp_path / "09_final" / "branded_cut.mp4"

    client = CanvaClient(Secrets(), mock=True)
    result = client.apply_branding(rough_cut, out_path, {"title": "t", "channel_name": "c"})

    assert result == out_path
    assert out_path.read_bytes() == b"FAKE_VIDEO_BYTES"


def test_configured_requires_all_three_credentials():
    assert not CanvaClient(Secrets())._configured()
    assert not CanvaClient(Secrets(canva_brand_template_id="tmpl_1"))._configured()
    assert CanvaClient(
        Secrets(
            canva_brand_template_id="tmpl_1",
            canva_client_id="client_1",
            canva_client_secret="secret_1",
        )
    )._configured()
