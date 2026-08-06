"""Downloads/generates one image per non-reused scene, organized into
data/projects/<id>/07_images/<scene_id>/image.png. Content-hash cached via
manifest.json so a resumed run never re-spends image-gen credits on a scene
it already has."""
from __future__ import annotations

import shutil

from ystick.config import PROJECT_ROOT
from ystick.core.exceptions import FatalError
from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext, Stage
from ystick.integrations.image_gen_client import ImageGenClient
from ystick.utils.files import content_hash, read_json, write_json


class ImageGenerationStage(Stage):
    name = "image_generation"

    def run(self, ctx: ProjectContext) -> dict:
        prompts = read_json(ctx.project_dir / STAGE_FOLDERS["image_prompts"] / "image_prompts.json")
        out_dir = ctx.project_dir / STAGE_FOLDERS[self.name]
        manifest_path = out_dir / "manifest.json"
        manifest = read_json(manifest_path) if manifest_path.exists() else {}

        client = ImageGenClient(ctx.secrets, mock=ctx.mock)
        reference_image_path = PROJECT_ROOT / "config" / "reference_character.png"
        previous_image_path = reference_image_path if reference_image_path.exists() else None

        num_generated = num_cached = num_reused = 0
        for entry in prompts:
            scene_id = entry["scene_id"]
            scene_dir = out_dir / scene_id
            scene_dir.mkdir(parents=True, exist_ok=True)
            image_path = scene_dir / "image.png"

            if "reuse_scene" in entry:
                source_scene = entry["reuse_scene"]
                if source_scene not in manifest:
                    raise FatalError(f"{scene_id} reuses {source_scene}, but it has no image yet")
                shutil.copyfile(manifest[source_scene]["path"], image_path)
                manifest[scene_id] = {"path": str(image_path), "prompt_hash": manifest[source_scene]["prompt_hash"]}
                num_reused += 1
                continue

            prompt = entry["prompt"]
            phash = content_hash(prompt)
            cached = manifest.get(scene_id)
            if cached and cached.get("prompt_hash") == phash and image_path.exists():
                num_cached += 1
                previous_image_path = image_path
                continue

            client.generate(prompt, image_path, reference_image=previous_image_path)
            manifest[scene_id] = {"path": str(image_path), "prompt_hash": phash}
            previous_image_path = image_path
            num_generated += 1

        write_json(manifest_path, manifest)
        return {"generated": num_generated, "cached": num_cached, "reused": num_reused}
