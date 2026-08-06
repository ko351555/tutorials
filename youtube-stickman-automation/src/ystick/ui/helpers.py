"""Small utilities shared by the Streamlit pages — kept out of app.py/gates.py
so those stay focused on layout.

Project metadata (seed idea, target length, mock mode) is NOT duplicated
here — it lives in `data/projects/<id>/project.json`, owned by
`Orchestrator.init_project`/`load_project_meta`, so the CLI and UI can
never drift out of sync on what a project was set up to make."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from ystick.config import PROJECT_ROOT

# Files below this size are almost certainly --mock placeholders (a few
# bytes of literal text) rather than real media, so we show a caption
# instead of asking st.audio/st.video to render garbage.
_MOCK_MEDIA_SIZE_THRESHOLD = 2048


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
