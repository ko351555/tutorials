"""Small utilities shared by the Streamlit pages — kept out of app.py/gates.py
so those stay focused on layout."""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from ystick.config import PROJECT_ROOT

# Files below this size are almost certainly --mock placeholders (a few
# bytes of literal text) rather than real media, so we show a caption
# instead of asking st.audio/st.video to render garbage.
_MOCK_MEDIA_SIZE_THRESHOLD = 2048


def ui_meta_path(project_dir: Path) -> Path:
    return project_dir / "ui_meta.json"


def save_ui_meta(project_dir: Path, *, seed_idea: str, mock: bool) -> None:
    ui_meta_path(project_dir).write_text(json.dumps({"seed_idea": seed_idea, "mock": mock}))


def load_ui_meta(project_dir: Path) -> dict:
    path = ui_meta_path(project_dir)
    if not path.exists():
        return {"seed_idea": "", "mock": True}
    return json.loads(path.read_text())


def safe_audio(path: Path, label: str = "Narration") -> None:
    if not path.exists():
        st.caption(f"{label}: not generated yet.")
        return
    if path.stat().st_size < _MOCK_MEDIA_SIZE_THRESHOLD:
        st.caption(f"{label}: mock placeholder (not real audio) — {path.name}")
        return
    st.audio(str(path))


def safe_video(path: Path, label: str = "Video") -> None:
    if not path.exists():
        st.caption(f"{label}: not generated yet.")
        return
    if path.stat().st_size < _MOCK_MEDIA_SIZE_THRESHOLD:
        st.caption(f"{label}: mock placeholder (not a real video) — {path.name}")
        return
    st.video(str(path))


def tail_log(project_id: str, n: int = 60) -> str:
    log_path = PROJECT_ROOT / "logs" / f"{project_id}.log"
    if not log_path.exists():
        return "(no log file yet)"
    lines = log_path.read_text().splitlines()[-n:]
    return "\n".join(lines) or "(empty)"
