# Dream Sanctum Music — Video Automation

Automates the assembly + upload stage of your workflow. It replaces the
Canva (loop video) → Clideo (loop audio) → CapCut (assemble to final length)
→ manual YouTube upload chain with one script.

**Google Flow and Suno stay manual** — there's no automation API for either,
so you keep generating the 10s silent clip and the music track by hand, the
same way you do today.

## What this does and doesn't automate

| Step | Before | Now |
|---|---|---|
| ChatGPT image prompt | manual | manual (unchanged) |
| Google Flow → 10s silent video clip | manual | manual (unchanged) |
| Canva → loop clip to 15 min | manual | **automatic** (ffmpeg) |
| Suno → generate + download MP3 | manual | manual (unchanged) |
| Clideo → loop audio to 30 min | manual | **automatic** (ffmpeg) |
| CapCut → assemble to 5-8 hours | manual | **automatic** (ffmpeg, one pass) |
| Title / description / tags | manual retype | **automatic** (parsed from your content file) |
| YouTube upload | manual | **automatic** (YouTube Data API) |

The three ffmpeg-replaced steps collapse into a single pass: the silent clip
and the music track are each looped independently straight to the final
target length (5 or 8 hours) and muxed together. There's no quality or
smoothness benefit to building 15-minute/30-minute intermediate files by
hand — that staging only existed because Canva/Clideo/CapCut have export
limits ffmpeg doesn't have.

## One-time setup

1. **Install ffmpeg** (also installs `ffprobe`):
   - macOS: `brew install ffmpeg`
   - Ubuntu/Debian: `sudo apt install ffmpeg`
   - Windows: https://ffmpeg.org/download.html

2. **Install Python dependencies**:
   ```
   pip install -r requirements.txt
   ```

3. **Authorize YouTube upload access** (one-time, ~5 minutes):
   - Go to https://console.cloud.google.com/, create a project.
   - Enable the **YouTube Data API v3** for it (APIs & Services → Library).
   - Create an OAuth client ID of type **Desktop app** (APIs & Services →
     Credentials), download the JSON, save it as
     `dreamsanctum-video-automation/client_secrets.json`.
   - The first upload will open a browser to sign in with the Google account
     that owns `@DreamSanctumMusic` and ask you to approve access. After
     that a `token.json` is cached and every future upload is unattended —
     no browser needed until you revoke access.
   - `client_secrets.json` and `token.json` are already in `.gitignore` —
     never commit them, they grant upload access to your channel.

## Web UI (recommended)

A local browser UI wraps the whole flow so you don't type CLI commands. It
works through videos **one at a time**, not as one big batch form:

```
python webui/app.py
# open http://127.0.0.1:5000
```

From there:
1. Upload the content file for this batch → it parses and lists every
   `VIDEO <n>` as a clickable row (title, tag count).
2. Click one video. Its detail panel opens with the **Google Flow prompt**
   and **Suno prompt** (each with a Copy button) — go generate that clip and
   track in those two apps, using those exact prompts.
3. Attach the clip + track (and optional thumbnail) you downloaded, confirm
   the hours (pre-filled by reading "8 Hours" / "5 Hours" etc. straight out
   of the video's own title — override it if you want), and click
   **Run this video**.
4. It assembles (ffmpeg loops the clip and track to the target length and
   muxes them together) with a live progress bar. Pick the next video from
   the list whenever you're ready — nothing forces you to queue all 10 up
   front.

**Nothing uploads to YouTube automatically.** If a video's "Upload to
YouTube" box is checked, its job stops right after assembly with status
`awaiting_approval`: you get an inline `<video>` player to scrub through the
finished file, and **Approve & upload** / **Reject** buttons. Only clicking
Approve starts the upload — Reject leaves the assembled MP4 on disk and goes
no further. This is the "ask permission before the next step" gate: assembly
runs unattended, but the upload — the one step that's hard to undo — always
waits for you.

It's the same `assemble_only()` / `upload_only()` functions from
`create_video.py` underneath, just called as two separate steps instead of
straight through — the UI is just a browser front end for them, so
everything in "One-time setup" below still applies (ffmpeg installed,
`client_secrets.json` in place).

**Security note:** this binds to `127.0.0.1` only and has no login — it's a
single-user local tool. Don't expose it to a network; anyone who can reach it
can trigger uploads to your channel.

## Single video (CLI)

Once you've downloaded the clip from Google Flow and the track from Suno:

```
python create_video.py \
  --content-file sample_content/dream_sanctum_videos_11_15.md \
  --video-number 11 \
  --clip ~/Downloads/video_11_clip.mp4 \
  --audio ~/Downloads/video_11_track.mp3 \
  --hours 8 \
  --output-dir ./output \
  --upload --privacy private
```

This looks up VIDEO 11 in the content file, builds the 8-hour MP4, and
uploads it with that video's title/description/tags pulled straight from the
content file — nothing retyped by hand.

Add `--dry-run` first to see the ffmpeg command without running it, or to
preview the upload metadata without uploading.

Add `--publish-at 2026-08-15T09:00:00Z` to schedule instead of uploading as
private/public immediately (YouTube auto-publishes at that time).

## Batch of ~10 videos (your normal workflow)

```
cp batch_config.example.yaml batch_config.yaml
# edit batch_config.yaml: point each `clip:`/`audio:` at your downloaded files
python batch_run.py batch_config.yaml
```

`batch_run.py` processes every video listed in the config, keeps going if one
entry fails (bad path, missing content-file entry, etc.), and prints a
pass/fail summary at the end with the resulting YouTube links. It can also
auto-stagger scheduled publish times across the batch (see the `schedule:`
block in `batch_config.example.yaml`) so you don't have to hand-pick 10
publish times.

Run with `python batch_run.py batch_config.yaml --dry-run` first to sanity
check the whole batch (ffmpeg commands + intended upload metadata) without
touching ffmpeg or YouTube.

## Content file format

`content_parser.py` expects the same format Claude already produces for you:
videos separated by a line of `=`, each starting with `VIDEO <n> — <NAME>`,
with `YOUTUBE TITLE:`, `YOUTUBE DESCRIPTION:` (hashtags included at the end
of the description, used to populate the video's tags), `SHORTS TITLE:` etc.

**You can upload the .pdf directly** — both the web UI and
`--content-file`/`content_file:` on the CLI accept a `.pdf` and extract its
text automatically (via PyMuPDF), no manual conversion to markdown needed.
The extraction also undoes the PDF's own line-wrapping so titles come out as
a single clean line and descriptions keep their real paragraph breaks. `.md`
and `.txt` still work too, read as-is.

Two sample `.md` files are included, transcribed from real content-file PDFs:

- `sample_content/dream_sanctum_videos_11_15.md` — anxiety/mental health category
- `sample_content/dream_sanctum_categories_5_6_7.md` — world music/seasonal/children,
  which also has `SUNO PROMPT:` and `LYRICS FIELD:` per video (the parser
  handles content files with or without these two fields — older files that
  don't have them just leave `suno_prompt`/`lyrics` empty)

Drop a new content file anywhere and point `--content-file` / `content_file:`
(CLI) or the upload button (web UI) at it — no code changes needed for a new
batch of videos.

To inspect what a content file parses to without running anything else:

```
python pipeline/content_parser.py sample_content/dream_sanctum_videos_11_15.md --video-number 11
```

## Files

- `pipeline/content_parser.py` — extracts title/description/tags/etc. per video from a content file
- `pipeline/assemble.py` — ffmpeg loop + mux (the Canva+Clideo+CapCut replacement)
- `pipeline/youtube_upload.py` — OAuth + resumable upload via YouTube Data API v3
- `create_video.py` — single-video CLI tying the three together
- `batch_run.py` — batch CLI for a full set of videos from `batch_config.yaml`
- `batch_config.example.yaml` — copy to `batch_config.yaml` and fill in your paths
- `webui/app.py` — local Flask server for the browser UI (uses the same functions as the CLI)
- `webui/templates/`, `webui/static/` — the browser UI itself

## Notes on file size

By default the final video is a fast, lossless stream-copy loop of your
source clip (`-c:v copy`) — no quality loss, but file size scales linearly
with how many times the clip repeats. A 10-second clip looped for 8 hours is
~2880 repeats, so a ~8MB source clip becomes a ~23GB output file.

Pass `--reencode --video-bitrate 2500k` (on `create_video.py`, `assemble.py`,
or per-video/globally in `batch_config.yaml`) to re-encode instead — much
smaller files (roughly 9GB for 8 hours at 2500kbps, tunable), which is a good
trade for these mostly-static ambient scenes. Re-encoding takes longer than
stream-copy looping since ffmpeg has to actually process every frame.
