"""Rich, per-gate approval screens and result views. Each render_* function
owns one stage's review UI and calls orch.approve(...) + st.rerun() itself
once the human is satisfied — the main app just dispatches to the right one."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from ystick.core.orchestrator import Orchestrator
from ystick.core.pipeline import STAGE_FOLDERS
from ystick.stages.stage7_image_generation import find_uploaded_image
from ystick.ui.helpers import safe_audio, safe_video
from ystick.utils.files import read_json, write_json

SCORE_LABELS = {
    "viral_potential": "Viral",
    "search_demand": "Search demand",
    "competition": "Low competition",
    "watch_time_potential": "Watch time",
    "monetization_potential": "Monetization",
}


def render_topic_selection(orch: Orchestrator, project_id: str, project_dir: Path) -> None:
    ideas_path = project_dir / STAGE_FOLDERS["topic_discovery"] / "ideas.json"
    ideas = read_json(ideas_path)

    st.subheader("🎯 Stage 1 — Pick a topic")
    st.caption("Ranked by weighted score across viral potential, search demand, competition, watch-time, and monetization.")

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
                if st.button("Select", key=f"select_idea_{i}", type="primary", use_container_width=True):
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
    if col1.button("💾 Save edits", use_container_width=True, disabled=edited == text):
        _save_script(script_dir, edited)
        st.success("Saved.")
        st.rerun()
    if col2.button("✅ Approve & Continue", type="primary", use_container_width=True):
        if edited != text:
            _save_script(script_dir, edited)
        orch.approve(project_id, "script_review", {})
        st.rerun()


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
    st.dataframe(rows, use_container_width=True, hide_index=True)

    if st.button("✅ Approve & Continue", type="primary"):
        orch.approve(project_id, "storyboard_review", {})
        st.rerun()


def render_image_upload(orch: Orchestrator, project_id: str, project_dir: Path) -> None:
    """Fires automatically when IMAGE_GEN_PROVIDER=manual — no image-gen API
    key needed at all. Shows each scene's prompt (copy it into ChatGPT or
    whatever tool you like) and a slot to upload the result directly."""
    prompts = read_json(project_dir / STAGE_FOLDERS["image_prompts"] / "image_prompts.json")
    images_dir = project_dir / STAGE_FOLDERS["image_generation"]
    needs_upload = [e for e in prompts if "prompt" in e]

    st.subheader("🖼️ Generate images manually, then upload them here")
    st.caption(
        "No image-gen API key needed — copy each prompt below into ChatGPT "
        "(or any image tool), download the result, and upload it in the "
        "matching slot. Scenes that reuse a previous image are handled "
        "automatically and don't need an upload."
    )

    uploaded_count = 0
    for entry in needs_upload:
        scene_id = entry["scene_id"]
        scene_dir = images_dir / scene_id
        existing = find_uploaded_image(scene_dir)
        if existing:
            uploaded_count += 1

        with st.container(border=True):
            st.markdown(f"**{scene_id}**" + ("  ✅" if existing else ""))
            st.code(entry["prompt"], language=None)
            cols = st.columns([1, 2])
            if existing:
                cols[0].image(str(existing), width=160)
            uploaded_file = cols[1].file_uploader(
                "Upload image", type=["png", "jpg", "jpeg", "webp"], key=f"upload_{scene_id}", label_visibility="collapsed"
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

    st.divider()
    total = len(needs_upload)
    st.progress(uploaded_count / total if total else 1.0, text=f"{uploaded_count} of {total} images uploaded")
    if st.button("✅ Approve & Continue", type="primary", disabled=uploaded_count < total):
        orch.approve(project_id, "image_upload", {})
        st.rerun()


def render_final_review(orch: Orchestrator, project_id: str, project_dir: Path) -> None:
    branded_cut = project_dir / STAGE_FOLDERS["canva_finishing"] / "branded_cut.mp4"

    st.subheader("🎞️ Stage 9 — Final review before packaging")
    st.caption("Last check before Stage 10 drafts YouTube title/description/tags and (optionally) uploads a private draft.")
    safe_video(branded_cut, "Branded cut")

    if st.button("✅ Approve & Continue", type="primary"):
        orch.approve(project_id, "final_review", {})
        st.rerun()


def render_results(project_dir: Path, mock: bool) -> None:
    packaging_path = project_dir / STAGE_FOLDERS["youtube_packaging"] / "packaging.json"
    if not packaging_path.exists():
        return
    packaging = read_json(packaging_path)

    st.subheader("📦 YouTube packaging")
    st.text_input("Title", value=packaging.get("title", ""))
    st.text_area("Description", value=packaging.get("description", ""), height=120)
    st.write("**Tags:** " + ", ".join(packaging.get("tags", [])))

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("Thumbnail text", value=packaging.get("thumbnail_text", ""))
        st.text_area("Thumbnail concept", value=packaging.get("thumbnail_concept", ""), height=80)
        st.text_area("Pinned comment", value=packaging.get("pinned_comment", ""), height=80)
    with col2:
        st.text_input("Shorts title", value=packaging.get("shorts_title", ""))
        st.text_area("Shorts description", value=packaging.get("shorts_description", ""), height=80)
        st.text_area("Community post", value=packaging.get("community_post", ""), height=80)

    if packaging.get("chapters"):
        st.write("**Chapters**")
        st.dataframe(packaging["chapters"], use_container_width=True, hide_index=True)

    upload = packaging.get("youtube_upload", {})
    if upload.get("status") == "mock":
        st.info("Mock mode: no real YouTube upload was made.")
    elif upload.get("video_id"):
        st.success(f"Draft uploaded to YouTube (private): video_id={upload['video_id']}")

    branded_cut = project_dir / STAGE_FOLDERS["canva_finishing"] / "branded_cut.mp4"
    safe_video(branded_cut, "Final video")


def render_asset_browser(project_dir: Path) -> None:
    tabs = st.tabs(["Script", "Audio", "Images", "Storyboard", "Video", "Packaging"])

    script_path = project_dir / STAGE_FOLDERS["script_generation"] / "script.md"
    with tabs[0]:
        st.code(script_path.read_text(), language="markdown") if script_path.exists() else st.caption("Not generated yet.")

    with tabs[1]:
        safe_audio(project_dir / STAGE_FOLDERS["voice_generation"] / "narration.mp3")

    with tabs[2]:
        manifest_path = project_dir / STAGE_FOLDERS["image_generation"] / "manifest.json"
        if manifest_path.exists():
            manifest = read_json(manifest_path)
            cols = st.columns(4)
            for i, (scene_id, entry) in enumerate(sorted(manifest.items())):
                img_path = Path(entry["path"])
                if img_path.exists():
                    cols[i % 4].image(str(img_path), caption=scene_id, use_container_width=True)
        else:
            st.caption("Not generated yet.")

    with tabs[3]:
        storyboard_path = project_dir / STAGE_FOLDERS["scene_planning"] / "storyboard.json"
        if storyboard_path.exists():
            st.dataframe(read_json(storyboard_path), use_container_width=True, hide_index=True)
        else:
            st.caption("Not generated yet.")

    with tabs[4]:
        branded_cut = project_dir / STAGE_FOLDERS["canva_finishing"] / "branded_cut.mp4"
        rough_cut = project_dir / STAGE_FOLDERS["video_assembly"] / "rough_cut.mp4"
        if branded_cut.exists():
            st.caption(f"`{branded_cut}` (branded)")
            safe_video(branded_cut, "Branded cut")
        elif rough_cut.exists():
            st.caption(f"`{rough_cut}` (rough cut — branding not applied yet)")
            safe_video(rough_cut, "Rough cut")
        else:
            st.caption("Not generated yet.")

    with tabs[5]:
        packaging_path = project_dir / STAGE_FOLDERS["youtube_packaging"] / "packaging.json"
        if packaging_path.exists():
            st.caption(f"`{packaging_path}`")
            st.json(read_json(packaging_path))
        else:
            st.caption("Not generated yet.")
