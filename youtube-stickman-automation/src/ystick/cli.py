from __future__ import annotations

import typer

from ystick.approvals import describe_pending
from ystick.core.orchestrator import GATE_AFTER_STAGE, Orchestrator
from ystick.logging_conf import configure_logging
from ystick.state.models import AWAITING_APPROVAL, DONE, FAILED
from ystick.utils.ids import new_project_id

app = typer.Typer(help="Automation pipeline for stickman/doodle YouTube videos.")


@app.command()
def new(idea: str, mock: bool = typer.Option(False, help="Run with no external API calls (fixture data).")):
    """Create a project from a video idea or niche, and run it up to the first approval gate."""
    project_id = new_project_id(idea)
    orch = Orchestrator()
    orch.init_project(project_id, idea)
    log = configure_logging(project_id)
    typer.echo(f"Created project: {project_id}")
    _run_and_report(orch, project_id, idea, mock, log)


@app.command()
def run(
    project_id: str,
    mock: bool = typer.Option(False, help="Run with no external API calls (fixture data)."),
    force: bool = typer.Option(False, help="Re-run stages even if already marked done."),
):
    """Resume/continue a project's pipeline from wherever it left off."""
    orch = Orchestrator()
    log = configure_logging(project_id)
    _run_and_report(orch, project_id, "", mock, log, force=force)


@app.command()
def status(project_id: str):
    """Show per-stage status for a project."""
    orch = Orchestrator()
    for s in orch.status(project_id):
        typer.echo(f"{s.stage:20s} {s.status:18s} attempts={s.attempts} last_error={s.last_error or '-'}")


@app.command()
def approve(
    project_id: str,
    stage: str = typer.Option(..., "--stage", help=f"One of: {', '.join(GATE_AFTER_STAGE)}"),
    select: int = typer.Option(0, help="For topic_selection: index of the idea to proceed with."),
):
    """Record an approval decision for a pending gate, then continue the run."""
    if stage not in GATE_AFTER_STAGE:
        typer.echo(f"Unknown gate {stage!r}. Valid gates: {', '.join(GATE_AFTER_STAGE)}")
        raise typer.Exit(1)
    orch = Orchestrator()
    orch.approve(project_id, stage, {"select": select})
    typer.echo(f"Approved {stage} for {project_id}. Run `ystick run {project_id}` to continue.")


@app.command("force-from")
def force_from(project_id: str, stage: str):
    """Reset a project's state from STAGE onward and re-run those stages
    next time (does not delete already-produced files)."""
    orch = Orchestrator()
    orch.force_from(project_id, stage)
    typer.echo(f"Reset {project_id} from {stage} onward.")


def _run_and_report(orch: Orchestrator, project_id: str, seed_idea: str, mock: bool, log, force: bool = False):
    result = orch.run(project_id, seed_idea=seed_idea, mock=mock, log=log, force=force)
    if result == "done":
        typer.echo(f"[{project_id}] pipeline complete.")
    elif result == "awaiting_approval":
        pending_gate = next(
            (g for g in GATE_AFTER_STAGE if orch.store.get_approval(project_id, g) is None
             and orch.store.get_status(project_id, GATE_AFTER_STAGE[g]).status == AWAITING_APPROVAL),
            None,
        )
        typer.echo(f"[{project_id}] paused for approval: {pending_gate}")
        if pending_gate:
            typer.echo(describe_pending(orch.project_dir(project_id), pending_gate))
            typer.echo(f"\nRun: ystick approve {project_id} --stage {pending_gate} [--select N]")
    elif result == "failed":
        typer.echo(f"[{project_id}] failed — see `ystick status {project_id}` and logs/{project_id}.log")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
