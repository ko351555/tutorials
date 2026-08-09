let contentFilePath = null;
let parsedVideos = [];
let knownJobIds = [];
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
  el("parsed-summary").textContent =
    `Parsed ${parsedVideos.length} video(s): ` +
    parsedVideos.map((v) => `#${v.video_number}`).join(", ");

  el("settings-card").style.display = "";
  el("videos-card").style.display = "";
  renderVideoRows();
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

function renderVideoRows() {
  const container = el("video-rows");
  container.innerHTML = "";
  parsedVideos.forEach((v) => {
    const row = document.createElement("div");
    row.className = "video-row";
    row.dataset.videoNumber = v.video_number;
    row.innerHTML = `
      <h3><label><input type="checkbox" class="include-check" checked> VIDEO ${v.video_number} — ${v.video_name}</label></h3>
      <div class="title">${v.youtube_title || "(no title parsed)"} · ${v.tag_count} tags</div>

      <details class="prompt-details">
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
        <label>Hours
          <input type="number" class="hours-input" value="8" step="0.5" min="0.1">
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
    `;
    if (v.google_flow_video_prompt) {
      row.querySelector(".prompt-copy-slot-gf").appendChild(copyBtn(v.google_flow_video_prompt));
    }
    if (v.suno_prompt) {
      row.querySelector(".prompt-copy-slot-suno").appendChild(copyBtn(v.suno_prompt));
    }
    container.appendChild(row);
  });
}

el("start-batch-btn").addEventListener("click", async () => {
  const errBox = el("start-batch-error");
  errBox.textContent = "";

  if (!contentFilePath) {
    errBox.textContent = "Parse a content file first.";
    return;
  }

  const fd = new FormData();
  fd.append("content_file_path", contentFilePath);
  fd.append("reencode", el("reencode-check").checked ? "true" : "false");
  fd.append("video_bitrate", el("video-bitrate").value);
  fd.append("category_id", el("category-id").value);
  fd.append("output_dir", el("output-dir").value);

  const rows = [];
  const rowEls = document.querySelectorAll(".video-row");
  let missing = [];

  rowEls.forEach((rowEl) => {
    if (!rowEl.querySelector(".include-check").checked) return;

    const vn = rowEl.dataset.videoNumber;
    const clipFile = rowEl.querySelector(".clip-input").files[0];
    const audioFile = rowEl.querySelector(".audio-input").files[0];
    const thumbFile = rowEl.querySelector(".thumb-input").files[0];

    if (!clipFile || !audioFile) {
      missing.push(vn);
      return;
    }

    fd.append(`clip_${vn}`, clipFile);
    fd.append(`audio_${vn}`, audioFile);
    if (thumbFile) fd.append(`thumbnail_${vn}`, thumbFile);

    const publishLocal = rowEl.querySelector(".publish-input").value;
    rows.push({
      video_number: Number(vn),
      hours: Number(rowEl.querySelector(".hours-input").value),
      privacy: rowEl.querySelector(".privacy-input").value,
      publish_at: publishLocal ? new Date(publishLocal).toISOString().replace(/\.\d{3}Z$/, "Z") : null,
      upload: rowEl.querySelector(".upload-check").checked,
    });
  });

  if (missing.length) {
    errBox.textContent = `Missing clip and/or audio file for video(s): ${missing.join(", ")}`;
    return;
  }
  if (!rows.length) {
    errBox.textContent = "No videos included in this batch.";
    return;
  }

  fd.append("rows", JSON.stringify(rows));

  el("start-batch-btn").disabled = true;
  const res = await fetch("/api/jobs/batch", { method: "POST", body: fd });
  const data = await res.json();
  el("start-batch-btn").disabled = false;

  if (data.error) {
    errBox.textContent = data.error;
    return;
  }

  const failed = (data.jobs || []).filter((j) => j.error);
  if (failed.length) {
    errBox.textContent = "Some videos couldn't be queued: " + failed.map((f) => `#${f.video_number} (${f.error})`).join(", ");
  }

  const newIds = (data.jobs || []).filter((j) => j.job_id).map((j) => j.job_id);
  knownJobIds = [...new Set([...knownJobIds, ...newIds])];

  el("jobs-card").style.display = "";
  startPolling();
});

function startPolling() {
  if (pollTimer) return;
  pollTimer = setInterval(pollJobs, 2000);
  pollJobs();
}

function stopPolling() {
  clearInterval(pollTimer);
  pollTimer = null;
}

const TERMINAL_STATUSES = ["done", "error", "rejected", "awaiting_approval"];

async function pollJobs() {
  const res = await fetch("/api/jobs");
  const jobs = await res.json();
  renderJobs(jobs);

  const allSettled = jobs.length > 0 && jobs.every((j) => TERMINAL_STATUSES.includes(j.status));
  if (allSettled) stopPolling();
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
