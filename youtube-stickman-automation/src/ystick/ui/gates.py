"""Rich, per-gate approval screens and result views. Each render_* function
owns one stage's review UI and calls orch.approve(...) + st.rerun() itself
once the human is satisfied — the main app just dispatches to the right one."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from ystick.core.orchestrator import Orchestrator
from ystick.core.pipeline import STAGE_DESCRIPTIONS, STAGE_FOLDERS, STAGE_LABELS, STAGE_ORDER
from ystick.stages.stage7_image_generation import find_uploaded_image
from ystick.state.models import DONE
from ystick.ui.helpers import safe_audio, safe_video
from ystick.utils.files import read_json, write_json

SCORE_LABELS = {
    "viral_potential": "Viral",
    "search_demand": "Search demand",
    "competition": "Low competition",
    "watch_time_potential": "Watch time",
    "monetization_potential": "Monetization",
}


def _next_stage_note(after_stage: str) -> str:
    """'Continuing will start Stage N: <label> — <what it does>', or a
    completion note if this is the last gate. Shown under every gate's
    continue button so it's always clear what happens next, not just
    what's happening now."""
    idx = STAGE_ORDER.index(after_stage)
    if idx + 1 < len(STAGE_ORDER):
        nxt = STAGE_ORDER[idx + 1]
        return f"➡️ Next: **{STAGE_LABELS[nxt]}** — {STAGE_DESCRIPTIONS[nxt]}"
    return "➡️ This is the last stage before the pipeline is complete."


def render_topic_selection(orch: Orchestrator, project_id: str, project_dir: Path) -> None:
    ideas_path = project_dir / STAGE_FOLDERS["topic_discovery"] / "ideas.json"
    ideas = read_json(ideas_path)

    st.subheader("🎯 Stage 1 — Pick a topic")
    st.caption("Ranked by weighted score across viral potential, search demand, competition, watch-time, and monetization.")
    st.caption(_next_stage_note("topic_discovery"))

    for i, idea in enumerate(ideas):
        with st.container(border=True):
            left, right = st.columns([5, 1])
            with left:
                st.markdown(f"**{idea['title']}**")
                st.write(idea.get("one_line_pitch", ""))
                score_cols = st.columns(len(SCORE_LABELS))
                for sc, (key, label) in zip(score_cols, SCORE_LABELS.items()):
                    if key in idea:
                        sc.metric(label, idea[key])
            with right:
                st.metric("Score", idea["weighted_score"])
                if st.button("Select", key=f"select_idea_{i}", type="primary", width='stretch'):
                    orch.approve(project_id, "topic_selection", {"select": i})
                    st.rerun()


def render_script_review(orch: Orchestrator, project_id: str, project_dir: Path) -> None:
    script_dir = project_dir / STAGE_FOLDERS["script_generation"]
    script_md_path = script_dir / "script.md"
    text = script_md_path.read_text()

    st.subheader("📝 Stage 2 — Review the script")
    st.caption("Edit freely — saved edits feed straight into voice generation.")
    edited = st.text_area("Narration script", value=text, height=420, label_visibility="collapsed")

    col1, col2 = st.columns(2)
    if col1.button("💾 Save edits", width='stretch', disabled=edited == text):
        _save_script(script_dir, edited)
        st.success("Saved.")
        st.rerun()
    if col2.button("✅ Approve & Continue", type="primary", width='stretch'):
        if edited != text:
            _save_script(script_dir, edited)
        orch.approve(project_id, "script_review", {})
        st.rerun()
    st.caption(_next_stage_note("script_generation"))


def _save_script(script_dir: Path, text: str) -> None:
    (script_dir / "script.md").write_text(text)
    script_json_path = script_dir / "script.json"
    script_json = read_json(script_json_path)
    script_json["text"] = text
    write_json(script_json_path, script_json)


def render_storyboard_review(orch: Orchestrator, project_id: str, project_dir: Path) -> None:
    storyboard = read_json(project_dir / STAGE_FOLDERS["scene_planning"] / "storyboard.json")

    st.subheader("🎬 Stage 5 — Review storyboard pacing")
    st.caption(f"{len(storyboard)} scenes planned.")

    rows = [
        {
            "Scene": s["scene_id"],
            "Start": f"{s['start_ms'] / 1000:.1f}s",
            "Duration": f"{s['duration_ms'] / 1000:.1f}s",
            "Holds previous image": "yes" if s["hold_previous_image"] else "",
            "Narration": (s["narration_excerpt"][:100] + "…") if len(s["narration_excerpt"]) > 100 else s["narration_excerpt"],
        }
        for s in storyboard
    ]
    st.dataframe(rows, width='stretch', hide_index=True)

    if st.button("✅ Approve & Continue", type="primary"):
        orch.approve(project_id, "storyboard_review", {})
        st.rerun()
    st.caption(_next_stage_note("scene_planning"))


def _render_upload_widgets(project_dir: Path) -> tuple[int, int]:
    """The per-scene prompt + upload-slot UI, shared by the image_upload
    gate and the failure-recovery view below. Returns (uploaded, total)."""
    prompts = read_json(project_dir / STAGE_FOLDERS["image_prompts"] / "image_prompts.json")
    images_dir = project_dir / STAGE_FOLDERS["image_generation"]
    needs_upload = [e for e in prompts if "prompt" in e]

    uploaded_count = 0
    for step, entry in enumerate(needs_upload, start=1):
        scene_id = entry["scene_id"]
        scene_dir = images_dir / scene_id
        existing = find_uploaded_image(scene_dir)
        if existing:
            uploaded_count += 1

        with st.container(border=True):
            st.markdown(f"**Step {step} of {len(needs_upload)} — {scene_id}**")
            st.code(entry["prompt"], language=None)
            cols = st.columns([1, 2])
            with cols[0]:
                if existing:
                    st.image(str(existing), width=160)
                    st.success(f"Uploaded: {existing.name}")
                else:
                    st.info("Waiting for upload")
            uploaded_file = cols[1].file_uploader(
                "Upload image" if not existing else "Replace image",
                type=["png", "jpg", "jpeg", "webp"],
                key=f"upload_{scene_id}",
            )
            # file_uploader keeps returning the same UploadedFile on every
            # rerun (not just the moment it's selected) — guard on file_id
            # so we don't rewrite-and-rerun forever for an upload already
            # processed.
            processed_key = f"_processed_upload_{scene_id}"
            if uploaded_file is not None and st.session_state.get(processed_key) != uploaded_file.file_id:
                scene_dir.mkdir(parents=True, exist_ok=True)
                ext = Path(uploaded_file.name).suffix or ".png"
                (scene_dir / f"image{ext}").write_bytes(uploaded_file.getvalue())
                st.session_state[processed_key] = uploaded_file.file_id
                st.rerun()

    return uploaded_count, len(needs_upload)


def render_image_upload(orch: Orchestrator, project_id: str, project_dir: Path) -> None:
    """Fires automatically when IMAGE_GEN_PROVIDER=manual — no image-gen API
    key needed at all. Shows each scene's prompt (copy it into ChatGPT or
    whatever tool you like) and a slot to upload the result directly."""
    st.subheader("🖼️ Generate images manually, then upload them here")
    st.caption(
        "No image-gen API key needed — copy each prompt below into ChatGPT "
        "(or any image tool), download the result, and upload it in the "
        "matching slot. Scenes that reuse a previous image are handled "
        "automatically and don't need an upload."
    )

    uploaded_count, total = _render_upload_widgets(project_dir)

    st.divider()
    st.progress(uploaded_count / total if total else 1.0, text=f"{uploaded_count} of {total} images uploaded")
    if st.button("✅ Approve & Continue", type="primary", disabled=uploaded_count < total):
        orch.approve(project_id, "image_upload", {})
        st.rerun()
    if uploaded_count < total:
        st.caption(f"Upload the remaining {total - uploaded_count} image(s) to continue.")
    else:
        st.caption(_next_stage_note("image_prompts"))


def render_image_upload_recovery(project_dir: Path) -> None:
    """Shown instead of a plain error box when Stage 7 (Images) fails in
    manual mode. This happens when a project already passed the Prompts
    stage — and so the image_upload gate — in an earlier run, before
    IMAGE_GEN_PROVIDER was set to manual; the gate can't fire
    retroactively for a stage that's already done. Same upload widgets as
    the gate; the caller's Retry button re-runs Stage 7 once everything's
    uploaded — there's no approval to record here."""
    st.warning(
        "This project already passed the upload step in an earlier run, "
        "before manual image mode was turned on — so it went straight "
        "to trying the API and failed. Upload the images below, then "
        "click Retry."
    )
    uploaded_count, total = _render_upload_widgets(project_dir)
    st.progress(uploaded_count / total if total else 1.0, text=f"{uploaded_count} of {total} images uploaded")
    if uploaded_count < total:
        st.caption(f"Upload the remaining {total - uploaded_count} image(s), then click Retry below.")
    else:
        st.success("All images uploaded — click Retry below to continue.")


def render_final_review(orch: Orchestrator, project_id: str, project_dir: Path) -> None:
    final_cut = project_dir / STAGE_FOLDERS["caption_burn_in"] / "final_cut.mp4"

    st.subheader("🎞️ Final review before packaging")
    st.caption("Last check before Stage 10 drafts YouTube title/description/tags and (optionally) uploads a private draft.")
    safe_video(final_cut, "Final cut (branded + captioned)")

    if st.button("✅ Approve & Continue", type="primary"):
        orch.approve(project_id, "final_review", {})
        st.rerun()
    st.caption(_next_stage_note("caption_burn_in"))


# --- per-stage result previews -------------------------------------------
# One function per stage, each rendering whatever that stage actually
# produced. render_stage_results() below shows one of these per completed
# stage, so every step's output is inspectable, not just the current gate
# or a final summary.


def _preview_topic_discovery(project_dir: Path) -> None:
    path = project_dir / STAGE_FOLDERS["topic_discovery"] / "ideas.json"
    if not path.exists():
        st.caption("Not generated yet.")
        return
    ideas = read_json(path)
    rows = [
        {"Title": i["title"], "Score": i["weighted_score"], "Pitch": i.get("one_line_pitch", "")}
        for i in ideas
    ]
    st.dataframe(rows, width='stretch', hide_index=True)


def _preview_script_generation(project_dir: Path) -> None:
    path = project_dir / STAGE_FOLDERS["script_generation"] / "script.md"
    if not path.exists():
        st.caption("Not generated yet.")
        return
    st.code(path.read_text(), language="markdown")


def _preview_voice_generation(project_dir: Path) -> None:
    safe_audio(project_dir / STAGE_FOLDERS["voice_generation"] / "narration.mp3")


def _preview_timestamps(project_dir: Path) -> None:
    path = project_dir / STAGE_FOLDERS["timestamps"] / "transcript.json"
    if not path.exists():
        st.caption("Not generated yet.")
        return
    transcript = read_json(path)
    st.caption(f"{len(transcript['words'])} words, {len(transcript['sentences'])} sentences")
    st.dataframe(transcript["sentences"], width='stretch', hide_index=True)


def _preview_scene_planning(project_dir: Path) -> None:
    path = project_dir / STAGE_FOLDERS["scene_planning"] / "storyboard.json"
    if not path.exists():
        st.caption("Not generated yet.")
        return
    storyboard = read_json(path)
    rows = [
        {
            "Scene": s["scene_id"],
            "Start": f"{s['start_ms'] / 1000:.1f}s",
            "Duration": f"{s['duration_ms'] / 1000:.1f}s",
            "Holds previous image": "yes" if s["hold_previous_image"] else "",
            "Narration": (s["narration_excerpt"][:100] + "…") if len(s["narration_excerpt"]) > 100 else s["narration_excerpt"],
        }
        for s in storyboard
    ]
    st.dataframe(rows, width='stretch', hide_index=True)


def _preview_image_prompts(project_dir: Path) -> None:
    path = project_dir / STAGE_FOLDERS["image_prompts"] / "image_prompts.json"
    if not path.exists():
        st.caption("Not generated yet.")
        return
    for entry in read_json(path):
        if "prompt" in entry:
            st.markdown(f"**{entry['scene_id']}**")
            st.code(entry["prompt"], language=None)
        else:
            st.caption(f"{entry['scene_id']}: reuses {entry['reuse_scene']}'s image")


def _preview_image_generation(project_dir: Path) -> None:
    path = project_dir / STAGE_FOLDERS["image_generation"] / "manifest.json"
    if not path.exists():
        st.caption("Not generated yet.")
        return
    manifest = read_json(path)
    cols = st.columns(4)
    for i, (scene_id, entry) in enumerate(sorted(manifest.items())):
        img_path = Path(entry["path"])
        if img_path.exists():
            cols[i % 4].image(str(img_path), caption=scene_id, width='stretch')


def _preview_video_assembly(project_dir: Path) -> None:
    path = project_dir / STAGE_FOLDERS["video_assembly"] / "rough_cut.mp4"
    st.caption(f"`{path}`")
    safe_video(path, "Rough cut")


def _preview_canva_finishing(project_dir: Path) -> None:
    path = project_dir / STAGE_FOLDERS["canva_finishing"] / "branded_cut.mp4"
    st.caption(f"`{path}`")
    safe_video(path, "Branded cut")


def _preview_caption_burn_in(project_dir: Path) -> None:
    path = project_dir / STAGE_FOLDERS["caption_burn_in"] / "final_cut.mp4"
    st.caption(f"`{path}`")
    safe_video(path, "Final cut (branded + captioned)")


def _preview_youtube_packaging(project_dir: Path) -> None:
    path = project_dir / STAGE_FOLDERS["youtube_packaging"] / "packaging.json"
    if not path.exists():
        st.caption("Not generated yet.")
        return
    packaging = read_json(path)

    st.text_input("Title", value=packaging.get("title", ""), key="preview_title")
    st.text_area("Description", value=packaging.get("description", ""), height=120, key="preview_description")

    st.write("**Tags** — copy this straight into YouTube Studio's tags field:")
    tags = packaging.get("tags", [])
    st.code(", ".join(tags) if tags else "(none generated)", language=None)

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Thumbnail text", value=packaging.get("thumbnail_text", ""), key="preview_thumb_text")
        st.text_area("Pinned comment", value=packaging.get("pinned_comment", ""), height=80, key="preview_pinned")
    with col2:
        st.text_input("Shorts title", value=packaging.get("shorts_title", ""), key="preview_shorts_title")
        st.text_area("Shorts description", value=packaging.get("shorts_description", ""), height=80, key="preview_shorts_desc")
        st.text_area("Community post", value=packaging.get("community_post", ""), height=80, key="preview_community")

    if packaging.get("chapters"):
        st.write("**Chapters**")
        st.dataframe(packaging["chapters"], width='stretch', hide_index=True)

    thumbnail_prompts = packaging.get("thumbnail_prompts", [])
    if thumbnail_prompts:
        st.write("**5 high-CTR thumbnail prompts** — paste any of these into ChatGPT/DALL-E/Gemini to generate a thumbnail:")
        for i, thumb_prompt in enumerate(thumbnail_prompts, start=1):
            st.caption(f"Option {i}")
            st.code(thumb_prompt, language=None)

    upload = packaging.get("youtube_upload", {})
    if upload.get("status") == "mock":
        st.info("Mock mode: no real YouTube upload was made.")
    elif upload.get("video_id"):
        st.success(f"Draft uploaded to YouTube (private): video_id={upload['video_id']}")


STAGE_PREVIEWS = {
    "topic_discovery": _preview_topic_discovery,
    "script_generation": _preview_script_generation,
    "voice_generation": _preview_voice_generation,
    "timestamps": _preview_timestamps,
    "scene_planning": _preview_scene_planning,
    "image_prompts": _preview_image_prompts,
    "image_generation": _preview_image_generation,
    "video_assembly": _preview_video_assembly,
    "canva_finishing": _preview_canva_finishing,
    "caption_burn_in": _preview_caption_burn_in,
    "youtube_packaging": _preview_youtube_packaging,
}


def render_stage_results(project_dir: Path, status_by_stage: dict) -> None:
    """One expander per completed stage with that stage's actual output.
    Stages currently at an approval gate are skipped here — their active
    gate screen above already shows the full interactive detail."""
    completed = [s for s in STAGE_ORDER if status_by_stage[s].status == DONE]
    if not completed:
        st.info("Nothing completed yet — results will appear here as soon as the first stage finishes. Check the **Pipeline** tab to start or continue the run.")
        return
    st.subheader("📋 Results so far")
    for stage_name in completed:
        with st.expander(STAGE_LABELS[stage_name], expanded=(stage_name == completed[-1])):
            STAGE_PREVIEWS[stage_name](project_dir)
