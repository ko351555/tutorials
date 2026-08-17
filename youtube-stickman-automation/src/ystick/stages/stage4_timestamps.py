from __future__ import annotations

from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext, Stage
from ystick.integrations.transcription_client import build_transcription_client
from ystick.utils.files import read_json, write_json


class TimestampsStage(Stage):
    name = "timestamps"

    def run(self, ctx: ProjectContext) -> dict:
        audio_dir = ctx.project_dir / STAGE_FOLDERS["voice_generation"]
        script_dir = ctx.project_dir / STAGE_FOLDERS["script_generation"]
        script = read_json(script_dir / "script.json")

        client = build_transcription_client(ctx.secrets, ctx.mock, script_text=script["text"])
        transcript = client.transcribe(audio_dir / "narration.mp3")

        out_dir = ctx.project_dir / STAGE_FOLDERS[self.name]
        write_json(out_dir / "transcript.json", transcript)
        return {"num_words": len(transcript["words"]), "num_sentences": len(transcript["sentences"])}
