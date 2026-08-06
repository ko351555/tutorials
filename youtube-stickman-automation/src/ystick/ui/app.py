"""Streamlit control panel for the pipeline.

Run with:
    ystick-ui
or directly:
    streamlit run src/ystick/ui/app.py
"""
from __future__ import annotations

import streamlit as st

from ystick.core.orchestrator import GATE_AFTER_STAGE, STAGE_TO_GATE, Orchestrator
from ystick.core.pipeline import STAGE_ORDER
from ystick.state.models import AWAITING_APPROVAL, DONE, FAILED
from ystick.ui import gates
from ystick.ui.helpers import load_ui_meta, save_ui_meta, tail_log
from ystick.utils.ids import new_project_id

st.set_page_config(page_title="Stickman YouTube Automation", page_icon="🎬", layout="wide")

STAGE_LABELS = {
    "topic_discovery": "Topic",
    "script_generation": "Script",
    "voice_generation": "Voice",
    "timestamps": "Timestamps",
    "scene_planning": "Storyboard",
    "image_prompts": "Prompts",
    "image_generation": "Images",
    "video_assembly": "Assembly",
    "canva_finishing": "Branding",
    "youtube_packaging": "Packaging",
}
STATUS_ICON = {"pending": "⚪", "running": "🔵", "awaiting_approval": "⏳", "done": "✅", "failed": "❌"}
GATE_RENDERERS = {
    "topic_selection": gates.render_topic_selection,
    "script_review": gates.render_script_review,
    "storyboard_review": gates.render_storyboard_review,
    "final_review": gates.render_final_review,
}


@st.cache_resource
def get_orchestrator() -> Orchestrator:
    return Orchestrator()


def run_with_progress(orch: Orchestrator, project_id: str, seed_idea: str, mock: bool) -> None:
    with st.status("Running pipeline…", expanded=True) as box:
        for event in orch.iter_run(project_id, seed_idea=seed_idea, mock=mock):
            stage = event.get("stage")
            label = STAGE_LABELS.get(stage, stage or "")
            status = event["status"]
            if status == "running":
                box.write(f"🔵 Running **{label}**…")
            elif status == "done":
                box.write(f"✅ **{label}** complete")
            elif status == "skipped":
                box.write(f"⏭️ {label} already done")
            elif status == "awaiting_approval":
                box.write(f"⏳ **{label}** complete — waiting for your approval")
                box.update(label="Paused for approval", state="complete")
            elif status == "failed":
                box.write(f"❌ **{label}** failed: {event.get('error')}")
                box.update(label=f"Failed at {label}", state="error")
            elif status == "pipeline_done":
                box.write("🎉 All stages complete!")
                box.update(label="Pipeline complete", state="complete")
    st.rerun()


def render_stage_tracker(status_by_stage: dict) -> None:
    cols = st.columns(len(STAGE_ORDER))
    for col, stage_name in zip(cols, STAGE_ORDER):
        s = status_by_stage[stage_name]
        col.markdown(
            f"<div style='text-align:center'>{STATUS_ICON[s.status]}"
            f"<br><span style='font-size:0.75em'>{STAGE_LABELS[stage_name]}</span></div>",
            unsafe_allow_html=True,
        )


def find_blocking_condition(orch: Orchestrator, project_id: str, status_by_stage: dict):
    for stage_name in STAGE_ORDER:
        s = status_by_stage[stage_name]
        if s.status == FAILED:
            return "failed", stage_name
        if s.status == AWAITING_APPROVAL:
            gate = STAGE_TO_GATE.get(stage_name)
            if gate and orch.store.get_approval(project_id, gate) is None:
                return "awaiting_approval", gate
    return None, None


def sidebar(orch: Orchestrator) -> str | None:
    st.sidebar.title("🎬 Stickman Automation")
    st.sidebar.caption("YouTube video pipeline control panel")

    projects = orch.list_projects()
    with st.sidebar.expander("➕ New project", expanded=not projects):
        idea = st.text_input("Video idea or niche", key="new_idea")
        mock = st.checkbox("Mock mode (no API calls, free)", value=True, key="new_mock")
        if st.button("Create project", type="primary", use_container_width=True, disabled=not idea.strip()):
            project_id = new_project_id(idea)
            orch.init_project(project_id, idea)
            save_ui_meta(orch.project_dir(project_id), seed_idea=idea, mock=mock)
            st.session_state["current_project"] = project_id
            st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("Projects")
    if not projects:
        st.sidebar.info("No projects yet — create one above.")
        return None

    current = st.session_state.get("current_project")
    default_idx = projects.index(current) if current in projects else 0
    return st.sidebar.radio("Select a project", projects, index=default_idx, label_visibility="collapsed")


def advanced_panel(orch: Orchestrator, project_id: str) -> None:
    with st.sidebar.expander("⚠️ Advanced"):
        stage = st.selectbox("Reset from stage", STAGE_ORDER, key="reset_stage")
        st.caption("Re-runs this stage and everything after it. Does not delete existing files.")
        if st.button("Reset", use_container_width=True):
            orch.force_from(project_id, stage)
            st.rerun()


def main() -> None:
    orch = get_orchestrator()
    project_id = sidebar(orch)
    if project_id is None:
        st.title("🎬 Stickman YouTube Automation")
        st.write("Create a project in the sidebar to get started.")
        return

    st.session_state["current_project"] = project_id
    project_dir = orch.project_dir(project_id)
    meta = load_ui_meta(project_dir)
    advanced_panel(orch, project_id)

    st.title(project_id)
    states = orch.status(project_id)
    status_by_stage = {s.stage: s for s in states}
    render_stage_tracker(status_by_stage)
    st.divider()

    kind, detail = find_blocking_condition(orch, project_id, status_by_stage)

    if kind == "failed":
        stage_name = detail
        s = status_by_stage[stage_name]
        st.error(
            f"Stage **{STAGE_LABELS[stage_name]}** failed (attempt {s.attempts}):\n\n```\n{s.last_error}\n```"
        )
        if st.button("🔁 Retry", type="primary"):
            run_with_progress(orch, project_id, meta["seed_idea"], meta["mock"])
    elif kind == "awaiting_approval":
        GATE_RENDERERS[detail](orch, project_id, project_dir)
    elif all(s.status == DONE for s in states):
        st.success("Pipeline complete!")
        gates.render_results(project_dir, meta["mock"])
    else:
        st.info("Ready to run." + (" (mock mode)" if meta["mock"] else ""))
        if st.button("▶️ Run pipeline", type="primary"):
            run_with_progress(orch, project_id, meta["seed_idea"], meta["mock"])

    with st.expander("📁 Project assets"):
        gates.render_asset_browser(project_dir)

    with st.expander("🪵 Logs"):
        st.code(tail_log(project_id), language="json")


main()
