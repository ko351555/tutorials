"""Produces one image per non-reused scene, organized into
data/projects/<id>/07_images/<scene_id>/image.<ext>. Content-hash cached
via manifest.json so a resumed run never re-spends image-gen credits on a
scene it already has.

Two providers:
- API providers (openai, etc.) — ImageGenClient calls out and generates.
- "manual" — no API/key needed at all. Stage 6's prompts are shown to the
  user (via the image_upload approval gate in the UI, or by reading
  06_prompts/image_prompts.json directly) so they can generate images
  themselves (e.g. with ChatGPT, already covered by an existing
  subscription) and drop the result at
  07_images/<scene_id>/image.<png|jpg|jpeg|webp>. This stage then just
  verifies those files exist and builds the manifest from them — no
  network call, no billing.
"""
from __future__ import annotations

import shutil
from pathlib import Path

from ystick.config import PROJECT_ROOT
from ystick.core.exceptions import FatalError
from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext, Stage
from ystick.integrations.image_gen_client import ImageGenClient
from ystick.utils.files import content_hash, read_json, write_json

UPLOADED_IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def find_uploaded_image(scene_dir: Path) -> Path | None:
    for ext in UPLOADED_IMAGE_EXTS:
        candidate = scene_dir / f"image{ext}"
        if candidate.exists():
            return candidate
    return None


class ImageGenerationStage(Stage):
    name = "image_generation"

    def run(self, ctx: ProjectContext) -> dict:
        prompts = read_json(ctx.project_dir / STAGE_FOLDERS["image_prompts"] / "image_prompts.json")
        out_dir = ctx.project_dir / STAGE_FOLDERS[self.name]
        manifest_path = out_dir / "manifest.json"
        manifest = read_json(manifest_path) if manifest_path.exists() else {}

        manual_mode = (not ctx.mock) and ctx.secrets.image_gen_provider == "manual"
        client = None if manual_mode else ImageGenClient(ctx.secrets, mock=ctx.mock)
        reference_image_path = PROJECT_ROOT / "config" / "reference_character.png"
        previous_image_path = reference_image_path if reference_image_path.exists() else None

        num_generated = num_cached = num_reused = num_uploaded = 0
        missing: list[str] = []

        for entry in prompts:
            scene_id = entry["scene_id"]
            scene_dir = out_dir / scene_id
            scene_dir.mkdir(parents=True, exist_ok=True)
            image_path = scene_dir / "image.png"

            if "reuse_scene" in entry:
                source_scene = entry["reuse_scene"]
                if source_scene not in manifest:
                    if manual_mode:
                        # The scene it reuses is itself still awaiting an
                        # upload (already tracked in `missing`) — this one
                        # resolves on its own once that's uploaded and the
                        # stage re-runs. Not a separate thing to report.
                        continue
                    raise FatalError(f"{scene_id} reuses {source_scene}, but it has no image yet")
                source_path = Path(manifest[source_scene]["path"])
                dest_path = scene_dir / f"image{source_path.suffix}"
                shutil.copyfile(source_path, dest_path)
                manifest[scene_id] = {"path": str(dest_path), "prompt_hash": manifest[source_scene]["prompt_hash"]}
                num_reused += 1
                write_json(manifest_path, manifest)
                continue

            prompt = entry["prompt"]
            phash = content_hash(prompt)

            if manual_mode:
                uploaded = find_uploaded_image(scene_dir)
                if uploaded is None:
                    missing.append(scene_id)
                    continue
                manifest[scene_id] = {"path": str(uploaded), "prompt_hash": phash}
                previous_image_path = uploaded
                num_uploaded += 1
                write_json(manifest_path, manifest)
                continue

            cached = manifest.get(scene_id)
            if cached and cached.get("prompt_hash") == phash and image_path.exists():
                num_cached += 1
                previous_image_path = image_path
                continue

            client.generate(prompt, image_path, reference_image=previous_image_path)
            manifest[scene_id] = {"path": str(image_path), "prompt_hash": phash}
            previous_image_path = image_path
            num_generated += 1
            # Written per-scene, not just once at the end: if a later scene
            # fails (API error, quota, etc.) and the stage retries, already-
            # generated scenes must be skippable via the cache-hit check
            # above — otherwise a failure on scene 8 of 10 would silently
            # re-spend credits regenerating scenes 1-7 too.
            write_json(manifest_path, manifest)

        if missing:
            lines = [f"  - {out_dir / s / 'image.<png|jpg|jpeg|webp>'}" for s in missing]
            raise FatalError(
                f"manual image mode: {len(missing)} scene(s) still need an uploaded image "
                f"(use the image_upload gate in the UI, or place files at):\n" + "\n".join(lines)
            )

        return {"generated": num_generated, "cached": num_cached, "reused": num_reused, "uploaded": num_uploaded}
