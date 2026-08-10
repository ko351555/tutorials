let contentFilePath = null;
let parsedVideos = [];
let activeVideoNumber = null;
let jobsByVideo = {}; // video_number -> latest job summary from /api/jobs
let pollTimer = null;

const el = (id) => document.getElementById(id);

async function refreshYoutubeStatus() {
  const box = el("youtube-status");
  try {
    const res = await fetch("/api/youtube/status");
    const data = await res.json();
    if (data.connected) {
      box.className = "yt-status connected";
      box.textContent = "YouTube: connected";
    } else if (!data.client_secrets_present) {
      box.className = "yt-status disconnected";
      box.textContent = "YouTube: client_secrets.json not found — see README.md setup steps.";
    } else {
      box.className = "yt-status disconnected";
      box.innerHTML = "YouTube: not connected ";
      const btn = document.createElement("button");
      btn.textContent = "Connect";
      btn.onclick = connectYoutube;
      box.appendChild(btn);
    }
  } catch (e) {
    box.textContent = "YouTube: status check failed";
  }
}

async function connectYoutube() {
  const box = el("youtube-status");
  const res = await fetch("/api/youtube/connect", { method: "POST" });
  const data = await res.json();
  if (data.error) {
    box.textContent = "YouTube: " + data.error;
    return;
  }
  box.textContent = "YouTube: check the browser window that just opened to sign in…";
  let attempts = 0;
  const check = setInterval(async () => {
    attempts++;
    const s = await (await fetch("/api/youtube/status")).json();
    if (s.connected || attempts > 60) {
      clearInterval(check);
      refreshYoutubeStatus();
    }
  }, 3000);
}

el("parse-btn").addEventListener("click", async () => {
  const input = el("content-file-input");
  const errBox = el("parse-error");
  errBox.textContent = "";
  if (!input.files.length) {
    errBox.textContent = "Choose a content file first.";
    return;
  }
  const fd = new FormData();
  fd.append("content_file", input.files[0]);

  const res = await fetch("/api/content/parse", { method: "POST", body: fd });
  const data = await res.json();
  if (data.error) {
    errBox.textContent = data.error;
    return;
  }

  contentFilePath = data.content_file_path;
  parsedVideos = data.videos;
  activeVideoNumber = null;
  el("parsed-summary").textContent =
    `Parsed ${parsedVideos.length} video(s). Pick one below to work on.`;

  el("settings-card").style.display = "";
  el("videos-card").style.display = "";
  el("video-detail").innerHTML = "";
  renderVideoList();
});

function escapeHtml(s) {
  const d = document.createElement("div");
  d.textContent = s || "";
  return d.innerHTML;
}

function copyBtn(text) {
  const btn = document.createElement("button");
  btn.type = "button";
  btn.className = "copy-btn";
  btn.textContent = "Copy";
  btn.onclick = () => {
    navigator.clipboard.writeText(text);
    btn.textContent = "Copied";
    setTimeout(() => (btn.textContent = "Copy"), 1200);
  };
  return btn;
}

function statusBadge(status) {
  if (!status) return "";
  return `<span class="job-status ${status}">${status.replace("_", " ")}</span>`;
}

// ---- 3. Pick a video to work on ----

function renderVideoList() {
  const container = el("video-list");
  container.innerHTML = "";
  parsedVideos.forEach((v) => {
    const job = jobsByVideo[v.video_number];
    const row = document.createElement("div");
    row.className = "video-list-item" + (v.video_number === activeVideoNumber ? " active" : "");
    row.innerHTML = `
      <div class="video-list-main">
        <div class="video-list-title">VIDEO ${v.video_number} — ${v.video_name}</div>
        <div class="hint">${v.youtube_title || "(no title parsed)"}</div>
      </div>
      ${statusBadge(job && job.status)}
    `;
    row.addEventListener("click", () => selectVideo(v.video_number));
    container.appendChild(row);
  });
}

function selectVideo(videoNumber) {
  activeVideoNumber = videoNumber;
  renderVideoList();
  renderVideoDetail();
  el("video-detail").scrollIntoView({ behavior: "smooth", block: "start" });
}

function renderVideoDetail() {
  const container = el("video-detail");
  el("run-error").textContent = "";
  if (activeVideoNumber == null) {
    container.innerHTML = "";
    return;
  }

  const v = parsedVideos.find((p) => p.video_number === activeVideoNumber);
  const job = jobsByVideo[activeVideoNumber];
  const running = job && ["queued", "assembling", "queued_upload", "uploading"].includes(job.status);
  const defaultHours = v.suggested_hours || 8;

  container.innerHTML = `
    <div class="video-detail-panel">
      <h3>VIDEO ${v.video_number} — ${v.video_name}</h3>
      <div class="title">${v.youtube_title || "(no title parsed)"} · ${v.tag_count} tags</div>

      <details class="prompt-details" open>
        <summary>Prompts for Google Flow &amp; Suno (generate these first, then attach the files below)</summary>
        <div class="prompt-block">
          <div class="prompt-label">Google Flow video prompt <span class="prompt-copy-slot-gf"></span></div>
          <div class="prompt-text">${escapeHtml(v.google_flow_video_prompt) || "(none parsed)"}</div>
        </div>
        <div class="prompt-block">
          <div class="prompt-label">Suno prompt <span class="prompt-copy-slot-suno"></span></div>
          <div class="prompt-text">${escapeHtml(v.suno_prompt) || "(none parsed — type your own in Suno)"}</div>
        </div>
      </details>

      <div class="video-row-grid">
        <label>Clip (Google Flow, silent .mp4)
          <input type="file" class="clip-input" accept="video/mp4">
        </label>
        <label>Track (Suno .mp3)
          <input type="file" class="audio-input" accept="audio/mpeg,audio/mp3">
        </label>
        <label>Thumbnail (optional)
          <input type="file" class="thumb-input" accept="image/*">
        </label>
        <label>Hours ${v.suggested_hours ? `<span class="hint">(from script: ${v.suggested_hours}h)</span>` : ""}
          <input type="number" class="hours-input" value="${defaultHours}" step="0.5" min="0.1">
        </label>
        <label>Privacy
          <select class="privacy-input">
            <option value="private">private</option>
            <option value="unlisted">unlisted</option>
            <option value="public">public</option>
          </select>
        </label>
        <label>Schedule publish (optional)
          <input type="datetime-local" class="publish-input">
        </label>
        <label class="checkbox">
          <input type="checkbox" class="upload-check" checked> Upload to YouTube (you'll still approve after preview)
        </label>
      </div>

      <div class="row">
        <button id="run-video-btn" ${running ? "disabled" : ""}>${running ? "Running…" : "Run this video"}</button>
      </div>
    </div>
  `;

  const gfSlot = container.querySelector(".prompt-copy-slot-gf");
  if (v.google_flow_video_prompt && gfSlot) gfSlot.appendChild(copyBtn(v.google_flow_video_prompt));
  const sunoSlot = container.querySelector(".prompt-copy-slot-suno");
  if (v.suno_prompt && sunoSlot) sunoSlot.appendChild(copyBtn(v.suno_prompt));

  const runBtn = container.querySelector("#run-video-btn");
  if (runBtn) runBtn.addEventListener("click", runActiveVideo);
}

async function runActiveVideo() {
  const errBox = el("run-error");
  errBox.textContent = "";

  if (!contentFilePath) {
    errBox.textContent = "Parse a content file first.";
    return;
  }

  const panel = document.querySelector(".video-detail-panel");
  const vn = activeVideoNumber;
  const clipFile = panel.querySelector(".clip-input").files[0];
  const audioFile = panel.querySelector(".audio-input").files[0];
  const thumbFile = panel.querySelector(".thumb-input").files[0];

  if (!clipFile || !audioFile) {
    errBox.textContent = "Attach both a clip and a track before running this video.";
    return;
  }

  const fd = new FormData();
  fd.append("content_file_path", contentFilePath);
  fd.append("reencode", el("reencode-check").checked ? "true" : "false");
  fd.append("video_bitrate", el("video-bitrate").value);
  fd.append("category_id", el("category-id").value);
  fd.append("output_dir", el("output-dir").value);

  fd.append(`clip_${vn}`, clipFile);
  fd.append(`audio_${vn}`, audioFile);
  if (thumbFile) fd.append(`thumbnail_${vn}`, thumbFile);

  const publishLocal = panel.querySelector(".publish-input").value;
  const rows = [{
    video_number: vn,
    hours: Number(panel.querySelector(".hours-input").value),
    privacy: panel.querySelector(".privacy-input").value,
    publish_at: publishLocal ? new Date(publishLocal).toISOString().replace(/\.\d{3}Z$/, "Z") : null,
    upload: panel.querySelector(".upload-check").checked,
  }];
  fd.append("rows", JSON.stringify(rows));

  const runBtn = el("run-video-btn");
  runBtn.disabled = true;
  runBtn.textContent = "Starting…";

  const res = await fetch("/api/jobs/batch", { method: "POST", body: fd });
  const data = await res.json();

  const entry = (data.jobs || [])[0];
  if (!entry || entry.error) {
    errBox.textContent = (entry && entry.error) || data.error || "Could not start this video.";
    runBtn.disabled = false;
    runBtn.textContent = "Run this video";
    return;
  }

  jobsByVideo[vn] = { status: "queued" };
  renderVideoList();
  runBtn.textContent = "Running…";

  el("jobs-card").style.display = "";
  startPolling();
}

// ---- 4. Progress ----

function startPolling() {
  if (pollTimer) return;
  pollTimer = setInterval(pollJobs, 2000);
  pollJobs();
}

function stopPolling() {
  clearInterval(pollTimer);
  pollTimer = null;
}

const RUNNING_STATUSES = ["queued", "assembling", "queued_upload", "uploading"];

async function pollJobs() {
  const res = await fetch("/api/jobs");
  const jobs = await res.json();

  jobs.forEach((j) => { jobsByVideo[j.video_number] = j; });
  renderVideoList();
  if (activeVideoNumber != null) {
    const runBtn = el("run-video-btn");
    const activeJob = jobsByVideo[activeVideoNumber];
    if (runBtn && activeJob) {
      runBtn.disabled = RUNNING_STATUSES.includes(activeJob.status);
      runBtn.textContent = RUNNING_STATUSES.includes(activeJob.status) ? "Running…" : "Run this video";
    }
  }

  renderJobs(jobs);

  const stillRunning = jobs.some((j) => RUNNING_STATUSES.includes(j.status));
  if (!stillRunning) stopPolling();
}

function renderJobs(jobs) {
  const container = el("jobs-table");
  const openLogIds = new Set(
    [...container.querySelectorAll(".job-log.open")].map((n) => n.dataset.jobId)
  );

  container.innerHTML = "";
  jobs
    .slice()
    .sort((a, b) => a.video_number - b.video_number)
    .forEach((job) => {
      const div = document.createElement("div");
      div.className = "job";

      const ytLink = job.youtube_id
        ? `<a class="yt-link" href="https://youtu.be/${job.youtube_id}" target="_blank">youtu.be/${job.youtube_id}</a>`
        : "";
      const outPath = job.output_path ? `<div class="hint">${job.output_path}</div>` : "";
      const errMsg = job.error ? `<div class="error">${job.error}</div>` : "";

      const approvalBlock = job.status === "awaiting_approval" ? `
        <div class="approval-block">
          <p class="hint">Assembly finished. Preview it below, then approve to upload or reject to stop here — nothing has been sent to YouTube yet.</p>
          <video class="preview-player" controls preload="metadata" src="/api/jobs/${job.id}/preview"></video>
          <div class="row">
            <button class="approve-btn">Approve &amp; upload</button>
            <button class="reject-btn secondary-btn">Reject</button>
          </div>
        </div>
      ` : "";

      div.innerHTML = `
        <div class="job-head">
          <span>VIDEO ${job.video_number}${job.video_name ? " — " + job.video_name : ""}</span>
          <span class="job-status ${job.status}">${job.status.replace("_", " ")}</span>
        </div>
        <div class="progress-label">Assemble</div>
        <div class="progress-bar"><div class="progress-bar-fill" style="width:${job.assemble_pct || 0}%"></div></div>
        <div class="progress-label">Upload</div>
        <div class="progress-bar"><div class="progress-bar-fill" style="width:${job.upload_pct || 0}%"></div></div>
        ${approvalBlock}
        ${outPath}
        ${ytLink}
        ${errMsg}
        <div class="job-log" data-job-id="${job.id}"></div>
      `;

      div.querySelector(".job-head").addEventListener("click", () => toggleLog(job.id, div));

      const approveBtn = div.querySelector(".approve-btn");
      if (approveBtn) approveBtn.addEventListener("click", (e) => { e.stopPropagation(); decideJob(job.id, "approve"); });
      const rejectBtn = div.querySelector(".reject-btn");
      if (rejectBtn) rejectBtn.addEventListener("click", (e) => { e.stopPropagation(); decideJob(job.id, "reject"); });

      container.appendChild(div);

      if (openLogIds.has(job.id)) {
        toggleLog(job.id, div, true);
      }
    });
}

async function decideJob(jobId, action) {
  const res = await fetch(`/api/jobs/${jobId}/${action}`, { method: "POST" });
  const data = await res.json();
  if (data.error) {
    alert(data.error);
    return;
  }
  startPolling();
}

async function toggleLog(jobId, div, forceOpen) {
  const logEl = div.querySelector(".job-log");
  const willOpen = forceOpen || !logEl.classList.contains("open");
  if (!willOpen) {
    logEl.classList.remove("open");
    return;
  }
  const res = await fetch(`/api/jobs/${jobId}`);
  const data = await res.json();
  logEl.textContent = (data.log || []).join("\n") || "(no log yet)";
  logEl.classList.add("open");
}

refreshYoutubeStatus();
