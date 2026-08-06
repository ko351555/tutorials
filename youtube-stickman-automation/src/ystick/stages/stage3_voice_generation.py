from __future__ import annotations

import re
import subprocess
from pathlib import Path

from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext, Stage
from ystick.integrations.elevenlabs_client import ElevenLabsClient
from ystick.utils.files import read_json


def _chunk_text(text: str, max_chars: int) -> list[str]:
    sentences = re.split(r"(?<=[.!?])\s+", text.strip())
    chunks, current = [], ""
    for sentence in sentences:
        if len(current) + len(sentence) + 1 > max_chars and current:
            chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current.strip())
    return chunks


def _concat_audio(paths: list[Path], out_path: Path) -> None:
    if len(paths) == 1:
        out_path.write_bytes(paths[0].read_bytes())
        return
    list_file = out_path.parent / "audio_concat_list.txt"
    list_file.write_text("\n".join(f"file '{p.resolve()}'" for p in paths))
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file), "-c", "copy", str(out_path)],
        check=True, capture_output=True,
    )


class VoiceGenerationStage(Stage):
    name = "voice_generation"

    def run(self, ctx: ProjectContext) -> dict:
        script_dir = ctx.project_dir / STAGE_FOLDERS["script_generation"]
        script = read_json(script_dir / "script.json")

        cfg = ctx.settings.stages.voice_generation
        client = ElevenLabsClient(ctx.secrets, mock=ctx.mock)

        out_dir = ctx.project_dir / STAGE_FOLDERS[self.name]
        chunks_dir = out_dir / "chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)

        chunks = _chunk_text(script["text"], cfg.max_chars_per_request)
        chunk_paths = client.synthesize_chunked(chunks, chunks_dir)

        narration_path = out_dir / "narration.mp3"
        if ctx.mock:
            narration_path.write_bytes(b"MOCK_MP3_PLACEHOLDER")
        else:
            _concat_audio(chunk_paths, narration_path)

        return {"num_chunks": len(chunks), "narration_path": str(narration_path)}
