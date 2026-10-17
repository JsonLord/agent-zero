import pytest

from plugins.argus_supervisor.helpers.event_reducer import reduce
from plugins.argus_supervisor.helpers.models import CampaignState


def test_routine_status_metrics_stdout_and_revision_do_not_become_events():
    c = CampaignState("one", "job")
    remote = {"state": "working", "revision": "1", "stage": "training"}
    assert reduce(c, remote)
    assert (
        reduce(
            c,
            {
                **remote,
                "revision": "2",
                "stdout": "step 201",
                "loss": 0.2,
                "heartbeat_seq": 10,
            },
        )
        == []
    )


@pytest.mark.parametrize(
    "state,kind",
    [
        ("completed", "ATTEMPT_COMPLETED"),
        ("failed", "ATTEMPT_COMPLETED"),
        ("input-required", "BLOCKED"),
        ("auth-required", "BLOCKED"),
    ],
)
def test_significant_states_and_repeated_revision(state, kind):
    c = CampaignState("one", "job")
    events = reduce(c, {"state": state, "revision": "1"})
    assert events[0]["type"] == kind
    assert reduce(c, {"state": state, "revision": "1", "stdout": "more"}) == []
    assert all(e["type"] != "MISSION_COMPLETED" for e in events)
