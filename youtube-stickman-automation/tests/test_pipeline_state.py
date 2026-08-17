from pathlib import Path

from ystick.state.models import DONE, PENDING
from ystick.state.store import StateStore

STAGES = ["a", "b", "c"]


def test_ensure_project_creates_pending_rows(tmp_path: Path):
    store = StateStore(tmp_path / "runs.db")
    store.ensure_project("proj1", STAGES)
    states = store.list_stage_states("proj1", STAGES)
    assert [s.stage for s in states] == STAGES
    assert all(s.status == PENDING for s in states)


def test_set_status_and_resume(tmp_path: Path):
    store = StateStore(tmp_path / "runs.db")
    store.ensure_project("proj1", STAGES)
    store.set_status("proj1", "a", DONE)
    assert store.get_status("proj1", "a").status == DONE
    assert store.get_status("proj1", "b").status == PENDING


def test_approval_round_trip(tmp_path: Path):
    store = StateStore(tmp_path / "runs.db")
    store.ensure_project("proj1", STAGES)
    assert store.get_approval("proj1", "topic_selection") is None
    store.record_approval("proj1", "topic_selection", {"select": 2})
    assert store.get_approval("proj1", "topic_selection") == {"select": 2}


def test_reset_from(tmp_path: Path):
    store = StateStore(tmp_path / "runs.db")
    store.ensure_project("proj1", STAGES)
    for s in STAGES:
        store.set_status("proj1", s, DONE)
    store.reset_from("proj1", STAGES, "b")
    assert store.get_status("proj1", "a").status == DONE
    assert store.get_status("proj1", "b").status == PENDING
    assert store.get_status("proj1", "c").status == PENDING
