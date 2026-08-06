"""The state machine: run/resume a project through STAGE_ORDER, applying
retry policy per stage and stopping at approval gates."""
from __future__ import annotations

from pathlib import Path

from ystick.config import PROJECT_ROOT, AttrDict, Secrets, load_secrets, load_settings
from ystick.core.exceptions import FatalError, RetryableError
from ystick.core.pipeline import STAGE_FOLDERS, STAGE_ORDER, ProjectContext
from ystick.integrations.llm_client import LLMClient
from ystick.state.models import AWAITING_APPROVAL, DONE, FAILED, PENDING, RUNNING
from ystick.state.store import StateStore
from ystick.utils.retry import retrying

# gate name -> stage after which it fires, as configured in settings.yaml -> approvals
GATE_AFTER_STAGE = {
    "topic_selection": "topic_discovery",
    "script_review": "script_generation",
    "storyboard_review": "scene_planning",
    "final_review": "canva_finishing",
}
STAGE_TO_GATE = {v: k for k, v in GATE_AFTER_STAGE.items()}


def _build_stage_registry():
    # Imported lazily to avoid a stages -> core -> stages import cycle.
    from ystick.stages.stage1_topic_discovery import TopicDiscoveryStage
    from ystick.stages.stage2_script_generation import ScriptGenerationStage
    from ystick.stages.stage3_voice_generation import VoiceGenerationStage
    from ystick.stages.stage4_timestamps import TimestampsStage
    from ystick.stages.stage5_scene_planning import ScenePlanningStage
    from ystick.stages.stage6_image_prompts import ImagePromptsStage
    from ystick.stages.stage7_image_generation import ImageGenerationStage
    from ystick.stages.stage8_video_assembly import VideoAssemblyStage
    from ystick.stages.stage9_canva_finishing import CanvaFinishingStage
    from ystick.stages.stage10_youtube_packaging import YoutubePackagingStage

    stages = [
        TopicDiscoveryStage(),
        ScriptGenerationStage(),
        VoiceGenerationStage(),
        TimestampsStage(),
        ScenePlanningStage(),
        ImagePromptsStage(),
        ImageGenerationStage(),
        VideoAssemblyStage(),
        CanvaFinishingStage(),
        YoutubePackagingStage(),
    ]
    return {s.name: s for s in stages}


class Orchestrator:
    def __init__(self, projects_root: Path | None = None):
        self.settings: AttrDict = load_settings()
        self.secrets: Secrets = load_secrets()
        self.projects_root = projects_root or PROJECT_ROOT / "data" / "projects"
        self.store = StateStore(self.projects_root / "runs.db")
        self.stages = _build_stage_registry()

    def project_dir(self, project_id: str) -> Path:
        return self.projects_root / project_id

    def init_project(self, project_id: str, seed_idea: str) -> None:
        self.store.ensure_project(project_id, STAGE_ORDER)
        (self.project_dir(project_id)).mkdir(parents=True, exist_ok=True)

    def _build_context(self, project_id: str, seed_idea: str, mock: bool, log) -> ProjectContext:
        approvals = {gate: self.store.get_approval(project_id, gate) for gate in GATE_AFTER_STAGE}
        return ProjectContext(
            project_id=project_id,
            project_dir=self.project_dir(project_id),
            settings=self.settings,
            secrets=self.secrets,
            mock=mock,
            seed_idea=seed_idea,
            log=log,
            extra={"llm": LLMClient(self.secrets, mock=mock), "approvals": approvals},
        )

    def run(self, project_id: str, *, seed_idea: str = "", mock: bool = False, log=None, force: bool = False) -> str:
        """Runs stages until: pipeline completes, an approval gate blocks
        further progress, or a stage fails after exhausting retries.
        Returns one of: 'done', 'awaiting_approval', 'failed'."""
        ctx = self._build_context(project_id, seed_idea, mock, log)
        retry_cfg = self.settings.retry

        for stage_name in STAGE_ORDER:
            state = self.store.get_status(project_id, stage_name)
            if state.status == DONE and not force:
                continue
            if state.status == AWAITING_APPROVAL:
                gate = STAGE_TO_GATE.get(stage_name)
                if gate and self.store.get_approval(project_id, gate) is None:
                    if log:
                        log.info("blocked_on_approval", stage=stage_name, gate=gate)
                    return "awaiting_approval"
                # approval recorded since last run -> fall through and mark done
                self.store.set_status(project_id, stage_name, DONE)
                continue

            self.store.set_status(project_id, stage_name, RUNNING, bump_attempts=True)
            if log:
                log.info("stage_start", stage=stage_name)
            try:
                wrapped = retrying(
                    max_attempts=retry_cfg.max_attempts,
                    initial=retry_cfg.initial_backoff_seconds,
                    max_wait=retry_cfg.max_backoff_seconds,
                )(self.stages[stage_name].run)
                summary = wrapped(ctx)
            except (FatalError, RetryableError) as exc:
                self.store.set_status(project_id, stage_name, FAILED, error=str(exc))
                if log:
                    log.error("stage_failed", stage=stage_name, error=str(exc))
                return "failed"
            except Exception as exc:  # noqa: BLE001 - last-resort safety net
                self.store.set_status(project_id, stage_name, FAILED, error=repr(exc))
                if log:
                    log.error("stage_failed_unexpected", stage=stage_name, error=repr(exc))
                return "failed"

            if log:
                log.info("stage_complete", stage=stage_name, summary=summary)

            gate = STAGE_TO_GATE.get(stage_name)
            gate_enabled = gate and self.settings.approvals.get(gate, False)
            if gate_enabled and self.store.get_approval(project_id, gate) is None:
                self.store.set_status(project_id, stage_name, AWAITING_APPROVAL)
                if log:
                    log.info("awaiting_approval", stage=stage_name, gate=gate)
                return "awaiting_approval"

            self.store.set_status(project_id, stage_name, DONE)

        return "done"

    def status(self, project_id: str):
        return self.store.list_stage_states(project_id, STAGE_ORDER)

    def approve(self, project_id: str, gate: str, decision: dict) -> None:
        self.store.record_approval(project_id, gate, decision)
        stage_name = GATE_AFTER_STAGE[gate]
        self.store.set_status(project_id, stage_name, DONE)

    def force_from(self, project_id: str, from_stage: str) -> None:
        self.store.reset_from(project_id, STAGE_ORDER, from_stage)
