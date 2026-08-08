from __future__ import annotations

from typing import Optional

import typer

from ystick.approvals import describe_pending
from ystick.config import load_secrets
from ystick.core.orchestrator import GATE_AFTER_STAGE, Orchestrator
from ystick.integrations import canva_oauth
from ystick.logging_conf import configure_logging
from ystick.state.models import AWAITING_APPROVAL, DONE, FAILED
from ystick.utils.ids import new_project_id

app = typer.Typer(help="Automation pipeline for stickman/doodle YouTube videos.")


@app.command()
def new(
    idea: str = typer.Argument(
        "", help="A specific video idea, or blank to auto-pick from the channel's topics (config/channel_blueprint.yaml)."
    ),
    minutes: Optional[int] = typer.Option(
        None, "--minutes", help="Target narration length in minutes. Defaults to channel_blueprint.yaml's target_video_length_minutes."
    ),
    mock: bool = typer.Option(False, help="Run with no external API calls (fixture data)."),
):
    """Create a project from a video idea (or blank for the channel's default topics), and run it up to the first approval gate."""
    orch = Orchestrator()
    project_id = new_project_id(idea or orch.blueprint.name)
    orch.init_project(project_id, idea, target_minutes=minutes, mock=mock)
    meta = orch.load_project_meta(project_id)
    log = configure_logging(project_id)
    typer.echo(f"Created project: {project_id}")
    typer.echo(f"  Topic seed:    {idea or '(blank — will auto-pick from channel topics)'}")
    typer.echo(f"  Target length: {meta['target_minutes']} min")
    typer.echo(f"  Mode:          {'mock (no API calls)' if mock else 'live'}")
    _run_and_report(orch, project_id, log)


@app.command()
def run(
    project_id: str,
    mock: Optional[bool] = typer.Option(
        None, "--mock/--no-mock", help="Override the mode stored at creation time for this run."
    ),
    force: bool = typer.Option(False, help="Re-run stages even if already marked done."),
):
    """Resume/continue a project's pipeline from wherever it left off."""
    orch = Orchestrator()
    log = configure_logging(project_id)
    _run_and_report(orch, project_id, log, mock=mock, force=force)


@app.command()
def status(project_id: str):
    """Show per-stage status for a project, plus what it was set up to make."""
    orch = Orchestrator()
    meta = orch.load_project_meta(project_id)
    typer.echo(
        f"Topic seed: {meta['seed_idea'] or '(auto from channel topics)'}  |  "
        f"Target length: {meta['target_minutes']} min  |  "
        f"Mode: {'mock' if meta['mock'] else 'live'}"
    )
    typer.echo("")
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


@app.command("canva-auth")
def canva_auth():
    """One-time interactive OAuth2/PKCE authorization for Canva Connect.
    Requires CANVA_CLIENT_ID/CANVA_CLIENT_SECRET already set in .env (from
    a Canva integration at canva.com/developers, with CANVA_REDIRECT_URI
    registered as one of its Redirect URIs). Prints a CANVA_REFRESH_TOKEN
    to add to .env — after that, Canva branding just works, no further
    manual steps."""
    secrets = load_secrets()
    if not secrets.canva_client_id or not secrets.canva_client_secret:
        typer.echo("CANVA_CLIENT_ID and CANVA_CLIENT_SECRET must be set in .env first.")
        typer.echo("Get them from an integration at https://www.canva.com/developers/")
        raise typer.Exit(1)

    verifier, challenge = canva_oauth.generate_pkce_pair()
    state = canva_oauth.generate_state()
    auth_url = canva_oauth.build_authorization_url(secrets, state, challenge)

    typer.echo("1. Open this URL in a browser and approve access:\n")
    typer.echo(f"   {auth_url}\n")
    typer.echo(
        f"2. Canva will redirect to {secrets.canva_redirect_uri} — that page will "
        "likely show a browser error (nothing's listening there), which is fine. "
        "Copy the FULL URL from the address bar at that point.\n"
    )
    pasted = typer.prompt("3. Paste that URL here (or just the `code` value)")

    code = canva_oauth.extract_code_from_redirect(pasted, expected_state=state)
    tokens = canva_oauth.exchange_code_for_tokens(secrets, code, verifier)

    typer.echo("\nSuccess. Add this to your .env:\n")
    typer.echo(f"CANVA_REFRESH_TOKEN={tokens['refresh_token']}\n")
    typer.echo("Canva branding will work automatically from the next pipeline run.")


@app.command("force-from")
def force_from(project_id: str, stage: str):
    """Reset a project's state from STAGE onward and re-run those stages
    next time (does not delete already-produced files)."""
    orch = Orchestrator()
    orch.force_from(project_id, stage)
    typer.echo(f"Reset {project_id} from {stage} onward.")


def _run_and_report(orch: Orchestrator, project_id: str, log, mock: Optional[bool] = None, force: bool = False):
    result = orch.run(project_id, mock=mock, log=log, force=force)
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
