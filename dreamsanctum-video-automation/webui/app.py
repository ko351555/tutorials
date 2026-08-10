"""Local web UI for the DreamSanctum video pipeline.

Wraps content_parser / assemble / youtube_upload (via create_video's
assemble_only/upload_only) behind a browser UI: parse a content file, attach
a clip+track per video for up to a batch's worth of videos, and watch each
one assemble with a live progress bar. If the video is set to upload, the
job stops after assembly and waits for you to preview the file and click
Approve — nothing reaches YouTube without that explicit step.

Run:
    python webui/app.py
    # then open http://127.0.0.1:5000

This binds to 127.0.0.1 only and has no authentication — it's a single-user
local tool. Do not expose it to a network or the public internet: anyone who
can reach it can browse your uploaded files and trigger uploads to your
YouTube channel.
"""

from __future__ import annotations

import json
import queue
import sys
import threading
import uuid
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_file
from werkzeug.utils import secure_filename

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "pipeline"))

from content_parser import parse_content_file  # noqa: E402
from youtube_upload import (  # noqa: E402
    DEFAULT_CLIENT_SECRETS,
    DEFAULT_TOKEN_PATH,
    get_authenticated_service,
)
from create_video import assemble_only, upload_only  # noqa: E402

app = Flask(__name__)

UPLOAD_ROOT = ROOT / "webui_uploads"
UPLOAD_ROOT.mkdir(exist_ok=True)

JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()
# Items are (job_id, phase) — phase "assemble" or "upload" — so approving a
# job re-enters the same worker/queue for its upload phase instead of a
# separate mechanism.
JOB_QUEUE: "queue.Queue[tuple[str, str]]" = queue.Queue()


def _job_worker():
    # This loop must never die: it's the single long-lived worker behind
    # every job, past and future. Catching only Exception is not enough —
    # a handful of real-world failures (a Rust panic surfacing through a
    # ctypes/pyo3 dependency, SystemExit from a library) are BaseException
    # subclasses that would otherwise escape here, silently stalling every
    # job still in the queue with no error ever shown in the UI.
    while True:
        job_id, phase = JOB_QUEUE.get()
        try:
            if phase == "assemble":
                _run_assemble_phase(job_id)
            else:
                _run_upload_phase(job_id)
        except BaseException as e:  # noqa: BLE001 - see comment above
            with JOBS_LOCK:
                job = JOBS.get(job_id)
                if job:
                    job["status"] = "error"
                    job["error"] = f"Unexpected worker failure: {e}"
                    job["log"].append(f"ERROR: {e}")
        finally:
            JOB_QUEUE.task_done()


def _run_assemble_phase(job_id: str):
    with JOBS_LOCK:
        job = JOBS[job_id]
        job["status"] = "assembling"

    def log(msg: str):
        with JOBS_LOCK:
            job["log"].append(msg)

    def progress(phase: str, pct: float):
        with JOBS_LOCK:
            job[f"{phase}_pct"] = pct

    try:
        result = assemble_only(
            content_file=job["content_file"],
            video_number=job["video_number"],
            clip=job["clip_path"],
            audio=job["audio_path"],
            hours=job["hours"],
            output_dir=job["output_dir"],
            reencode=job["reencode"],
            video_bitrate=job["video_bitrate"],
            on_log=log,
            on_progress=progress,
        )
        with JOBS_LOCK:
            job["output_path"] = result["output_path"]
            job["video_name"] = result["video_name"]
            if job["upload"]:
                job["status"] = "awaiting_approval"
                job["log"].append(
                    "Assembly complete. Preview the video and click Approve to upload, or Reject to stop here."
                )
            else:
                job["status"] = "done"
    except Exception as e:  # noqa: BLE001 - report to the UI, keep the worker alive
        with JOBS_LOCK:
            job["status"] = "error"
            job["error"] = str(e)
            job["log"].append(f"ERROR: {e}")


def _run_upload_phase(job_id: str):
    with JOBS_LOCK:
        job = JOBS[job_id]
        job["status"] = "uploading"

    def log(msg: str):
        with JOBS_LOCK:
            job["log"].append(msg)

    def progress(phase: str, pct: float):
        with JOBS_LOCK:
            job[f"{phase}_pct"] = pct

    try:
        video_id = upload_only(
            content_file=job["content_file"],
            video_number=job["video_number"],
            output_path=job["output_path"],
            privacy=job["privacy"],
            publish_at=job["publish_at"],
            category_id=job["category_id"],
            thumbnail=job["thumbnail_path"],
            on_log=log,
            on_progress=progress,
        )
        with JOBS_LOCK:
            job["status"] = "done"
            job["youtube_id"] = video_id
    except Exception as e:  # noqa: BLE001
        with JOBS_LOCK:
            job["status"] = "error"
            job["error"] = str(e)
            job["log"].append(f"ERROR: {e}")


threading.Thread(target=_job_worker, daemon=True).start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/content/parse", methods=["POST"])
def parse_content():
    file = request.files.get("content_file")
    if not file or not file.filename:
        return jsonify({"error": "No content file uploaded"}), 400

    content_dir = UPLOAD_ROOT / "content"
    content_dir.mkdir(exist_ok=True)
    saved_name = f"{uuid.uuid4().hex[:8]}_{secure_filename(file.filename)}"
    saved_path = content_dir / saved_name
    file.save(saved_path)

    try:
        videos = parse_content_file(saved_path)
    except RuntimeError as e:
        # e.g. a .pdf uploaded but PyMuPDF isn't installed
        return jsonify({"error": str(e)}), 400
    except UnicodeDecodeError:
        return jsonify({
            "error": f"Could not read {file.filename} as text. Upload the .pdf directly, "
                     "or a .md/.txt export of it.",
        }), 400

    if not videos:
        return jsonify({"error": "No 'VIDEO <n> — <NAME>' blocks found in this file"}), 400

    return jsonify({
        "content_file_path": str(saved_path),
        "videos": [
            {
                "video_number": v.video_number,
                "video_name": v.video_name,
                "youtube_title": v.youtube_title,
                "tag_count": len(v.youtube_tags),
                "google_flow_video_prompt": v.google_flow_video_prompt,
                "suno_prompt": v.suno_prompt,
            }
            for v in videos
        ],
    })


@app.route("/api/jobs/batch", methods=["POST"])
def create_batch():
    content_file_path = request.form.get("content_file_path", "")
    if not content_file_path or not Path(content_file_path).exists():
        return jsonify({"error": "content_file_path missing or invalid — parse a content file first"}), 400

    try:
        rows = json.loads(request.form.get("rows", "[]"))
    except json.JSONDecodeError:
        return jsonify({"error": "rows must be a JSON array"}), 400

    reencode = request.form.get("reencode") == "true"
    video_bitrate = request.form.get("video_bitrate", "2500k")
    category_id = request.form.get("category_id", "10")
    output_dir = request.form.get("output_dir", "output")

    created = []
    for row in rows:
        vn = row.get("video_number")
        clip_file = request.files.get(f"clip_{vn}")
        audio_file = request.files.get(f"audio_{vn}")
        if not clip_file or not clip_file.filename or not audio_file or not audio_file.filename:
            created.append({"video_number": vn, "error": "missing clip or audio file"})
            continue

        vdir = UPLOAD_ROOT / str(vn)
        vdir.mkdir(parents=True, exist_ok=True)

        clip_path = vdir / secure_filename(clip_file.filename)
        clip_file.save(clip_path)

        audio_path = vdir / secure_filename(audio_file.filename)
        audio_file.save(audio_path)

        thumbnail_path = None
        thumb_file = request.files.get(f"thumbnail_{vn}")
        if thumb_file and thumb_file.filename:
            thumbnail_path = vdir / secure_filename(thumb_file.filename)
            thumb_file.save(thumbnail_path)

        job_id = uuid.uuid4().hex
        job = {
            "id": job_id,
            "video_number": vn,
            "video_name": row.get("video_name", ""),
            "content_file": content_file_path,
            "clip_path": str(clip_path),
            "audio_path": str(audio_path),
            "thumbnail_path": str(thumbnail_path) if thumbnail_path else None,
            "hours": float(row.get("hours", 8)),
            "output_dir": output_dir,
            "reencode": reencode,
            "video_bitrate": video_bitrate,
            "upload": bool(row.get("upload", True)),
            "privacy": row.get("privacy", "private"),
            "publish_at": row.get("publish_at") or None,
            "category_id": category_id,
            "status": "queued",
            "log": [],
            "assemble_pct": 0.0,
            "upload_pct": 0.0,
            "output_path": None,
            "youtube_id": None,
            "error": None,
        }
        with JOBS_LOCK:
            JOBS[job_id] = job
        JOB_QUEUE.put((job_id, "assemble"))
        created.append({"video_number": vn, "job_id": job_id})

    return jsonify({"jobs": created})


@app.route("/api/jobs/<job_id>/approve", methods=["POST"])
def approve_job(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "not found"}), 404
        if job["status"] != "awaiting_approval":
            return jsonify({"error": f"job is '{job['status']}', not awaiting approval"}), 400
        job["status"] = "queued_upload"
        job["log"].append("Upload approved.")
    JOB_QUEUE.put((job_id, "upload"))
    return jsonify({"status": "queued_upload"})


@app.route("/api/jobs/<job_id>/reject", methods=["POST"])
def reject_job(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "not found"}), 404
        if job["status"] != "awaiting_approval":
            return jsonify({"error": f"job is '{job['status']}', not awaiting approval"}), 400
        job["status"] = "rejected"
        job["log"].append(f"Upload rejected. Assembled file kept at {job['output_path']}.")
    return jsonify({"status": "rejected"})


@app.route("/api/jobs/<job_id>/preview")
def preview_job(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        output_path = job["output_path"] if job else None
    if not output_path or not Path(output_path).exists():
        abort(404)
    return send_file(output_path, mimetype="video/mp4", conditional=True)


@app.route("/api/jobs")
def list_jobs():
    with JOBS_LOCK:
        return jsonify([
            {k: v for k, v in job.items() if k != "log"}
            for job in JOBS.values()
        ])


@app.route("/api/jobs/<job_id>")
def get_job(job_id):
    with JOBS_LOCK:
        job = JOBS.get(job_id)
        if not job:
            return jsonify({"error": "not found"}), 404
        return jsonify(job)


@app.route("/api/youtube/status")
def youtube_status():
    return jsonify({
        "client_secrets_present": DEFAULT_CLIENT_SECRETS.exists(),
        "connected": DEFAULT_TOKEN_PATH.exists(),
    })


@app.route("/api/youtube/connect", methods=["POST"])
def youtube_connect():
    if not DEFAULT_CLIENT_SECRETS.exists():
        return jsonify({
            "error": f"{DEFAULT_CLIENT_SECRETS} not found. See README.md for the one-time OAuth setup steps.",
        }), 400

    def do_auth():
        try:
            get_authenticated_service()
        except Exception as e:  # noqa: BLE001 - surfaced via /api/youtube/status polling
            print(f"YouTube authorization failed: {e}")

    threading.Thread(target=do_auth, daemon=True).start()
    return jsonify({"status": "started", "message": "A browser window should open for Google sign-in."})


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
