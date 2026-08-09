"""Streamlit control panel for the pipeline.

Run with:
    ystick-ui
or directly:
    streamlit run src/ystick/ui/app.py
"""
from __future__ import annotations

import streamlit as st

from ystick.config import PROJECT_ROOT
from ystick.core.orchestrator import GATE_AFTER_STAGE, STAGE_TO_GATE, Orchestrator
from ystick.core.pipeline import STAGE_DESCRIPTIONS, STAGE_LABELS, STAGE_ORDER
from ystick.state.models import AWAITING_APPROVAL, DONE, FAILED, RUNNING
from ystick.ui import gates
from ystick.ui.helpers import load_starter_topics, tail_log
from ystick.utils.ids import new_project_id

st.set_page_config(page_title="Stickman YouTube Automation", page_icon="🎬", layout="wide")

STATUS_ICON = {"pending": "⚪", "running": "🔵", "awaiting_approval": "⏳", "done": "✅", "failed": "❌"}
GATE_RENDERERS = {
    "topic_selection": gates.render_topic_selection,
    "script_review": gates.render_script_review,
    "storyboard_review": gates.render_storyboard_review,
    "image_upload": gates.render_image_upload,
    "final_review": gates.render_final_review,
}

PROJECT_STATUS_LABEL = {
    "done": "✅ Complete",
    "failed": "❌ Failed",
    "awaiting_approval": "⏳ Awaiting approval",
    "running": "🔵 In progress",
    "pending": "⚪ Not started",
}


@st.cache_resource
def get_orchestrator() -> Orchestrator:
    return Orchestrator()


def _project_overall_status(orch: Orchestrator, project_id: str) -> str:
    """Collapses a project's per-stage statuses into one headline state for
    the sidebar list — otherwise every project just shows its bare ID and
    there's no way to tell a finished one from a stalled one without
    clicking into each in turn."""
    statuses = {s.status for s in orch.status(project_id)}
    if statuses == {DONE}:
        return "done"
    if FAILED in statuses:
        return "failed"
    if AWAITING_APPROVAL in statuses:
        return "awaiting_approval"
    if DONE in statuses or RUNNING in statuses:
        return "running"
    return "pending"


def run_with_progress(orch: Orchestrator, project_id: str) -> None:
    """Runs from wherever the project currently is, using the seed/target
    length/mock mode recorded in project.json at creation time — nothing
    to re-specify here."""
    total = len(STAGE_ORDER)
    progress_bar = st.progress(0.0, text="Starting…")
    st.caption(
        "Stages that call real APIs (voice, images) can take anywhere from "
        "seconds to a few minutes each — this bar only advances when a "
        "stage *finishes*, so a long pause on one stage is normal, not stuck."
    )
    with st.status("Running pipeline…", expanded=True) as box:
        for event in orch.iter_run(project_id):
            stage = event.get("stage")
            label = STAGE_LABELS.get(stage, stage or "")
            status = event["status"]
            idx = STAGE_ORDER.index(stage) if stage in STAGE_ORDER else total
            duration = event.get("duration_s")
            duration_str = f" ({duration}s)" if duration is not None else ""

            if status == "running":
                progress_bar.progress(idx / total, text=f"Stage {idx + 1} of {total}: {label}…")
                box.write(f"🔵 Running **{label}**…")
            elif status == "done":
                progress_bar.progress((idx + 1) / total, text=f"Stage {idx + 1} of {total}: {label} done")
                box.write(f"✅ **{label}** complete{duration_str}")
            elif status == "skipped":
                progress_bar.progress((idx + 1) / total, text=f"Stage {idx + 1} of {total}: {label} (already done)")
                box.write(f"⏭️ {label} already done")
            elif status == "awaiting_approval":
                progress_bar.progress((idx + 1) / total, text=f"Paused after stage {idx + 1} of {total}: {label}")
                box.write(f"⏳ **{label}** complete{duration_str} — waiting for your approval")
                box.update(label="Paused for approval", state="complete")
            elif status == "failed":
                box.write(f"❌ **{label}** failed{duration_str}: {event.get('error')}")
                box.update(label=f"Failed at {label}", state="error")
            elif status == "pipeline_done":
                progress_bar.progress(1.0, text="Complete")
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


def render_how_it_works(orch: Orchestrator) -> None:
    bp = orch.blueprint
    with st.expander("ℹ️ How this pipeline starts and ends — and what to expect at each stage", expanded=False):
        st.markdown(
            f"""
**Start:** you give it a specific video idea, or leave it blank and it
picks from **{bp.name}**'s topics ({', '.join(bp.topics)}), scored for
viral/search/competition/watch-time/monetization potential.

**Then it runs through 10 automated stages**, pausing only at the approval
gates you've enabled (shown ⏳ in the tracker):

**End:** a fully packaged, branded video sitting as a **private** YouTube
draft with title/description/tags/chapters/thumbnail concept ready — you
click Publish. Nothing goes live on its own.

Target narration length defaults to **{bp.target_video_length_minutes} min**
(from `channel_blueprint.yaml`) and is set per-project when you create it —
see the caption under the project title once a project is selected.
            """
        )
        rows = [
            {"#": i + 1, "Stage": STAGE_LABELS[s], "What happens": STAGE_DESCRIPTIONS[s]}
            for i, s in enumerate(STAGE_ORDER)
        ]
        st.dataframe(rows, width='stretch', hide_index=True)


def sidebar(orch: Orchestrator) -> str | None:
    bp = orch.blueprint
    st.sidebar.title(f"🎬 {bp.name}")
    st.sidebar.caption(bp.tagline)
    with st.sidebar.expander("Channel", expanded=False):
        st.write(bp.description.strip())
        st.caption(f"Topics: {', '.join(bp.topics)}")
        st.caption(f"New video every {bp.upload_cadence_days} days")
        st.caption(f"[{bp.youtube_url}]({bp.youtube_url})")
        st.caption(f"Business: {bp.business_email}")

    projects = orch.list_projects()

    starter_topics = load_starter_topics(PROJECT_ROOT / orch.settings.channel.content_strategy_path)
    if starter_topics:
        with st.sidebar.expander("💡 Starter ideas", expanded=False):
            st.caption("From the channel's content strategy — click one to use it below.")
            for i, topic in enumerate(starter_topics):
                if st.button(topic, key=f"starter_{i}", width='stretch'):
                    st.session_state["new_idea"] = topic
                    st.session_state["_expand_new_project"] = True
                    st.rerun()

    with st.sidebar.expander("➕ New project", expanded=st.session_state.get("_expand_new_project", not projects)):
        idea = st.text_input(
            "Video idea (optional)",
            key="new_idea",
            placeholder=f"Leave blank to auto-pick from: {', '.join(bp.topics)}",
        )
        minutes = st.number_input(
            "Target length (minutes)", min_value=1, max_value=60, value=bp.target_video_length_minutes, key="new_minutes"
        )
        mock = st.checkbox("Mock mode (no API calls, free)", value=True, key="new_mock")
        if st.button("Create project", type="primary", width='stretch'):
            project_id = new_project_id(idea or bp.name)
            orch.init_project(project_id, idea, target_minutes=int(minutes), mock=mock)
            st.session_state["current_project"] = project_id
            st.session_state["_expand_new_project"] = False
            st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("Projects")
    if not projects:
        st.sidebar.info("No projects yet — create one above.")
        return None

    # URL query param (?project=<id>) makes the current project bookmarkable
    # and shareable, and survives a plain page refresh — session_state alone
    # doesn't. session_state wins when both are present (e.g. right after
    # creating a project, before the query param below has been written).
    current = st.session_state.get("current_project") or st.query_params.get("project")
    default_idx = projects.index(current) if current in projects else 0

    def _format_project(pid: str) -> str:
        status = _project_overall_status(orch, pid)
        return f"{PROJECT_STATUS_LABEL[status]} — {pid}"

    selected = st.sidebar.radio(
        "Select a project", projects, index=default_idx, format_func=_format_project, label_visibility="collapsed"
    )
    if st.query_params.get("project") != selected:
        st.query_params["project"] = selected
    return selected


def advanced_panel(orch: Orchestrator, project_id: str) -> None:
    with st.sidebar.expander("⚠️ Advanced"):
        stage = st.selectbox(
            "Reset from stage", STAGE_ORDER, format_func=lambda s: STAGE_LABELS[s], key="reset_stage"
        )
        st.caption("Re-runs this stage and everything after it. Does not delete existing files.")
        if st.button("Reset", width='stretch'):
            orch.force_from(project_id, stage)
            st.rerun()


def main() -> None:
    orch = get_orchestrator()
    project_id = sidebar(orch)
    if project_id is None:
        st.title(f"🎬 {orch.blueprint.name}")
        st.write("Create a project in the sidebar to get started.")
        render_how_it_works(orch)
        return

    st.session_state["current_project"] = project_id
    project_dir = orch.project_dir(project_id)
    meta = orch.load_project_meta(project_id)
    advanced_panel(orch, project_id)

    st.title(project_id)
    st.caption(
        f"**Topic:** {meta['seed_idea'] or '(auto — picked from channel topics)'}  ·  "
        f"**Target length:** {meta['target_minutes']} min  ·  "
        f"**Mode:** {'mock (no API calls)' if meta['mock'] else 'live'}"
    )
    st.caption(f"📂 Output folder: `{project_dir}`")
    render_how_it_works(orch)

    states = orch.status(project_id)
    status_by_stage = {s.stage: s for s in states}

    tab_pipeline, tab_results = st.tabs(["🚀 Pipeline", "📋 Results"])

    with tab_pipeline:
        render_stage_tracker(status_by_stage)
        st.divider()

        # A button clicked this same script run doesn't retroactively hide
        # whatever was already drawn above it (the "Ready to run"/"Retry"
        # button and its context box) — Streamlit just keeps appending
        # below. So a button click only sets a flag + reruns; the actual
        # run (and everything that would otherwise sit stale above the
        # live progress) happens on the next run, once we already know to
        # skip straight to run_with_progress.
        if st.session_state.get("_run_requested") == project_id:
            st.session_state["_run_requested"] = None
            run_with_progress(orch, project_id)
        else:
            kind, detail = find_blocking_condition(orch, project_id, status_by_stage)

            if kind == "failed":
                stage_name = detail
                s = status_by_stage[stage_name]
                # A project that already passed the Prompts stage before manual
                # image mode was turned on skips straight past the image_upload
                # gate (it can't fire retroactively) and fails here instead —
                # show the same upload widgets rather than just an error dump.
                if stage_name == "image_generation" and not meta["mock"] and orch.secrets.image_gen_provider == "manual":
                    st.caption(f"Stage **{STAGE_LABELS[stage_name]}** — attempt {s.attempts}")
                    gates.render_image_upload_recovery(project_dir)
                else:
                    st.error(
                        f"Stage **{STAGE_LABELS[stage_name]}** failed (attempt {s.attempts}):\n\n```\n{s.last_error}\n```"
                    )
                if st.button("🔁 Retry", type="primary"):
                    st.session_state["_run_requested"] = project_id
                    st.rerun()
            elif kind == "awaiting_approval":
                GATE_RENDERERS[detail](orch, project_id, project_dir)
            elif all(s.status == DONE for s in states):
                st.success("Pipeline complete! Check the **Results** tab for everything it produced.")
            else:
                st.info("Ready to run." + (" (mock mode)" if meta["mock"] else ""))
                if st.button("▶️ Run pipeline", type="primary"):
                    st.session_state["_run_requested"] = project_id
                    st.rerun()

    with tab_results:
        gates.render_stage_results(project_dir, status_by_stage)

    with st.expander("🪵 Logs"):
        st.code(tail_log(project_id), language="json")


main()
