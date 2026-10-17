import pytest

from plugins.argus_supervisor.helpers.campaign_store import CampaignStore
from plugins.argus_supervisor.helpers.models import CampaignState, SupervisorError


def test_atomic_save_reload_and_locked_transactions(tmp_path):
    store = CampaignStore(tmp_path)
    store.create(CampaignState("one", "job"))
    reopened = CampaignStore(tmp_path)
    assert reopened.load("one").objective == "job"
    with (
        store.lock("one"),
        pytest.raises(SupervisorError, match="busy"),
        reopened.lock("one"),
    ):
        pass
    assert not list(tmp_path.rglob(".pending-*"))


@pytest.mark.parametrize("data", ["broken", "[]", "{}", '{"schema_version":2}'])
def test_corrupt_state_fails_closed_without_replacing_it(tmp_path, data):
    store = CampaignStore(tmp_path)
    path = tmp_path / "campaigns/one.json"
    path.write_text(data)
    with pytest.raises(SupervisorError, match="corrupt"):
        store.load("one")
    assert path.read_text() == data


def test_event_commit_contains_outbox_and_deduplicates(tmp_path):
    store = CampaignStore(tmp_path)
    c = CampaignState("one", "job")
    store.create(c)
    e = {"id": "event1", "type": "BLOCKED", "data": {"reason": "missing input"}}
    assert store.append_event(c, e)
    assert not store.append_event(c, e)
    assert store.load("one").events["event1"]["delivery"] == "pending"
    assert len((tmp_path / "events/one.jsonl").read_text().splitlines()) == 1


def test_interrupted_replace_preserves_previous_state(tmp_path, monkeypatch):
    import os

    store = CampaignStore(tmp_path)
    c = CampaignState("one", "job")
    store.create(c)
    c.objective = "changed"

    def fail(*args):
        raise OSError("simulated disk failure")

    monkeypatch.setattr(os, "replace", fail)
    with pytest.raises(OSError):
        store.save(c)
    assert store.load("one").objective == "job"
