"""Parse a Dream Sanctum "content file" (the markdown/text Claude produces with
image prompts, video prompts, YouTube title/description, Shorts and Instagram
copy for a batch of videos) into structured per-video metadata.

Expected input shape (one or more videos per file), matching the format used
in DreamSanctum_Videos_11_to_15_Complete.md.pdf:

    VIDEO 11 — ANXIETY RELIEF SLEEP MUSIC

    CHATGPT IMAGE PROMPT: ...
    GOOGLE FLOW VIDEO PROMPT: ...
    YOUTUBE TITLE: ...
    YOUTUBE DESCRIPTION: ...
    (body text, timestamps, hashtags)
    SHORTS TITLE: ...
    SHORTS OVERLAY TEXT: ...
    SHORTS CAPTION: ...
    INSTAGRAM OPTION 1 — ...
    ====================================================...
    VIDEO 12 — ...

Videos are separated by a line of `=` characters (any length >= 5). Fields
are separated by their own ALL-CAPS "LABEL:" markers, so each field runs
until the next known label (or the video separator).

Accepts the content file straight as a .pdf, .md or .txt — parse_content_file()
and get_video() both detect a .pdf by extension and extract its text (via
PyMuPDF) before parsing, so you don't need to convert Claude's PDF output to
markdown by hand first.
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

VIDEO_HEADER_RE = re.compile(r"VIDEO\s+(\d+)\s*[—\-–]\s*(.+)")

# Order matters: this defines where each field stops (start of the next
# label that appears in the source documents). Newer content files add
# SUNO PROMPT / LYRICS FIELD between the video prompt and the YouTube title
# (e.g. Categories 5-7) — older files (e.g. Videos 11-15) simply don't have
# them, which _extract_field handles fine since it just looks for whichever
# later label appears first.
FIELD_LABELS = [
    "CHATGPT IMAGE PROMPT",
    "GOOGLE FLOW VIDEO PROMPT",
    "SUNO PROMPT",
    "LYRICS FIELD",
    "YOUTUBE TITLE",
    "YOUTUBE DESCRIPTION",
    "SHORTS TITLE",
    "SHORTS OVERLAY TEXT",
    "SHORTS CAPTION",
]
# Instagram sections are numbered/free-form ("INSTAGRAM OPTION 1 — ...", "INSTAGRAM OPTION 2 — ...")
INSTAGRAM_LABEL_RE = re.compile(r"^INSTAGRAM OPTION\s+\d+", re.MULTILINE)

# Restricted to ASCII word chars: PDF text extraction sometimes leaves stray
# broken-emoji remnants like "# し #" at the end of a hashtag line, and a
# plain \w would pick "し" up as a bogus tag.
HASHTAG_RE = re.compile(r"#([A-Za-z0-9]+)")


@dataclass
class VideoMetadata:
    video_number: Optional[int]
    video_name: str
    chatgpt_image_prompt: str = ""
    google_flow_video_prompt: str = ""
    suno_prompt: str = ""
    lyrics: str = ""
    youtube_title: str = ""
    youtube_description: str = ""
    youtube_tags: list = field(default_factory=list)
    shorts_title: str = ""
    shorts_overlay_text: str = ""
    shorts_caption: str = ""
    instagram_captions: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _split_videos(text: str) -> list[str]:
    """Split the content file into one chunk of text per video."""
    # Normalize the various "====...====" separator lengths into a single marker.
    chunks = re.split(r"\n=+\n", text)
    # Drop chunks that don't contain a VIDEO header (title page, END OF CATEGORY footer, etc.)
    return [c for c in chunks if VIDEO_HEADER_RE.search(c)]


def _looks_like_sentence_end(line: str) -> bool:
    line = line.rstrip()
    if not line:
        return False
    ch = line[-1]
    if ch in ".!?\"')]":
        return True
    # Most emoji land in Unicode category So (Symbol, other) or Sk; PDF
    # extraction has no other signal that a line ending in one is a
    # paragraph's last line rather than a mid-sentence wrap.
    return unicodedata.category(ch) in ("So", "Sk")


def _dewrap(text: str) -> str:
    """Undo PDF-extraction line wrapping.

    Two input shapes need different handling, both of which show up in
    practice: markdown content files write one full (unwrapped) line per
    paragraph with a blank line between them — those blank lines are a
    reliable hard break. PDF text extraction instead gives one line per
    *visual* line with no blank line at paragraph boundaries at all, so a
    paragraph's last line has to be inferred: it's short relative to the
    column width and ends in sentence-final punctuation (or an emoji),
    whereas a mid-paragraph wrap fills the line.
    """
    lines = text.split("\n")
    max_len = max((len(l.strip()) for l in lines), default=0)
    short_threshold = max(max_len * 0.82, 20)

    paragraphs: list[str] = []
    buf: list[str] = []
    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            if buf:
                paragraphs.append(" ".join(buf))
                buf = []
            continue
        buf.append(line)
        if len(line) < short_threshold and _looks_like_sentence_end(line):
            paragraphs.append(" ".join(buf))
            buf = []
    if buf:
        paragraphs.append(" ".join(buf))

    return "\n\n".join(p for p in paragraphs if p)


def _extract_field(chunk: str, label: str, next_labels: list[str]) -> str:
    """Grab the text after `LABEL:` up to whichever of next_labels appears first."""
    start_match = re.search(re.escape(label) + r":", chunk)
    if not start_match:
        return ""
    start = start_match.end()

    end = len(chunk)
    for nl in next_labels:
        m = re.search(re.escape(nl) + r":", chunk[start:])
        if m:
            end = min(end, start + m.start())

    ig_match = INSTAGRAM_LABEL_RE.search(chunk[start:])
    if ig_match:
        end = min(end, start + ig_match.start())

    return _dewrap(chunk[start:end])


def _extract_instagram_captions(chunk: str) -> list[str]:
    captions = []
    matches = list(INSTAGRAM_LABEL_RE.finditer(chunk))
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(chunk)
        captions.append(_dewrap(chunk[start:end]))
    return captions


def parse_video_chunk(chunk: str) -> VideoMetadata:
    header = VIDEO_HEADER_RE.search(chunk)
    video_number = int(header.group(1)) if header else None
    video_name = header.group(2).strip() if header else "UNKNOWN"

    fields = {}
    for i, label in enumerate(FIELD_LABELS):
        fields[label] = _extract_field(chunk, label, FIELD_LABELS[i + 1:])

    tags = sorted(set(HASHTAG_RE.findall(fields["YOUTUBE DESCRIPTION"])), key=str.lower)

    return VideoMetadata(
        video_number=video_number,
        video_name=video_name,
        chatgpt_image_prompt=fields["CHATGPT IMAGE PROMPT"],
        google_flow_video_prompt=fields["GOOGLE FLOW VIDEO PROMPT"],
        suno_prompt=fields["SUNO PROMPT"],
        lyrics=fields["LYRICS FIELD"],
        youtube_title=fields["YOUTUBE TITLE"],
        youtube_description=fields["YOUTUBE DESCRIPTION"],
        youtube_tags=tags,
        shorts_title=fields["SHORTS TITLE"],
        shorts_overlay_text=fields["SHORTS OVERLAY TEXT"],
        shorts_caption=fields["SHORTS CAPTION"],
        instagram_captions=_extract_instagram_captions(chunk),
    )


def parse_content_text(text: str) -> list[VideoMetadata]:
    return [parse_video_chunk(c) for c in _split_videos(text)]


def extract_pdf_text(path: str | Path) -> str:
    """Extract plain text from a content-file PDF, page by page.

    page.get_text() already ends each page's text with its own trailing
    newline, so pages are concatenated directly (no extra separator) —
    adding one would turn every page boundary into a blank line, which
    _dewrap() would then read as a hard paragraph break even when a
    sentence or paragraph actually continues across the page seam.
    """
    try:
        import pymupdf
    except ImportError as e:
        raise RuntimeError(
            "Reading a .pdf content file requires PyMuPDF: pip install pymupdf"
        ) from e

    with pymupdf.open(str(path)) as doc:
        return "".join(page.get_text() for page in doc)


def parse_content_file(path: str | Path) -> list[VideoMetadata]:
    path = Path(path)
    if path.suffix.lower() == ".pdf":
        text = extract_pdf_text(path)
    else:
        text = path.read_text(encoding="utf-8")
    return parse_content_text(text)


def get_video(path: str | Path, video_number: int) -> VideoMetadata:
    for v in parse_content_file(path):
        if v.video_number == video_number:
            return v
    raise ValueError(f"VIDEO {video_number} not found in {path}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("content_file", help="Path to a Dream Sanctum content .pdf, .md or .txt file")
    ap.add_argument("--video-number", type=int, help="Only print this video number")
    ap.add_argument("--out", help="Write JSON to this path instead of stdout")
    args = ap.parse_args()

    videos = parse_content_file(args.content_file)
    if args.video_number is not None:
        videos = [v for v in videos if v.video_number == args.video_number]
        if not videos:
            raise SystemExit(f"VIDEO {args.video_number} not found")

    data = [v.to_dict() for v in videos]
    output = json.dumps(data, indent=2, ensure_ascii=False)

    if args.out:
        Path(args.out).write_text(output, encoding="utf-8")
        print(f"Wrote {len(data)} video(s) to {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()
