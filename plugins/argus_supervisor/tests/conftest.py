import time

import pytest_asyncio

from plugins.argus_supervisor.helpers.a2a_client import (
    EXT_METHODS,
    EXTENSION,
    OpenTrainingA2AClient,
)
from plugins.argus_supervisor.helpers.campaign_store import CampaignStore
from plugins.argus_supervisor.helpers.heartbeat import Supervisor
from plugins.argus_supervisor.helpers.models import CampaignState


class Remote:
    def __init__(self):
        self.calls = []
        self.lease = {
            "controller_id": "argus-openoperator",
            "epoch": 4,
            "expires_at": time.time() + 600,
        }
        self.task = {
            "id": "task-1",
            "status": {"state": "working"},
            "metadata": {
                "argus_supervisor": {
                    "revision": "1",
                    "stage": "training",
                    "attempt_id": "a1",
                }
            },
        }
        self.extension = True
        self.timeout = None
        self.applied_mutations = []

    async def transport(self, method, suffix, payload):
        if method == "GET":
            return {
                "name": "Fake OpenTraining",
                "skills": [],
                "capabilities": {
                    "extensions": [
                        {
                            "uri": EXTENSION,
                            "params": {
                                "lease_epoch_enforced": True,
                                "policy_enforced": True,
                                "operations": {**EXT_METHODS, "cancel": "tasks/cancel"},
                            },
                        }
                    ]
                    if self.extension
                    else []
                },
            }
        operation = payload["method"]
        self.calls.append((operation, payload["params"]))
        if operation == self.timeout:
            from plugins.argus_supervisor.helpers.models import AmbiguousMutation

            raise AmbiguousMutation("mutation_outcome_unknown")
        if operation in {
            "message/send",
            "tasks/cancel",
            "campaign/intervene",
            "campaign/renew_control",
            "campaign/release_control",
        }:
            params = payload["params"]
            authority = (
                params["metadata"]["argus_supervisor"]
                if operation == "message/send"
                else params
            )
            if (
                self.lease.get("epoch") != authority.get("controller_epoch")
                or self.lease.get("controller_id") != authority.get("controller_id")
                or self.lease.get("expires_at", 0) <= time.time()
            ):
                return {
                    "jsonrpc": "2.0",
                    "id": payload["id"],
                    "error": {"code": -32001, "message": "stale epoch"},
                }
            self.applied_mutations.append(operation)
        if operation == "tasks/get":
            result = self.task
        elif operation == "campaign/read_control":
            result = self.lease
        elif operation == "campaign/claim_control":
            self.lease = {**self.lease, "epoch": self.lease["epoch"] + 1}
            result = self.lease
        elif operation == "campaign/renew_control":
            self.lease = {**self.lease, "expires_at": time.time() + 600}
            result = self.lease
        elif operation == "campaign/release_control":
            self.lease = {}
            result = {}
        elif operation == "message/send":
            result = self.task
        elif operation == "campaign/request_status":
            result = {
                "request_id": payload["params"]["request_id"],
                "state": "applied",
                "task_id": "task-1",
            }
        else:
            result = self.task
        return {"jsonrpc": "2.0", "id": payload["id"], "result": result}


class Argus:
    def __init__(self):
        self.calls = []
        self.result = {
            "status": "observing",
            "review": {"status": "done", "source": "reviewer"},
        }

    async def notify(self, campaign, events, evidence, hint):
        self.calls.append((events, evidence, hint))
        return self.result

    async def status(self, campaign):
        return self.result

    async def bind(self, campaign):
        campaign.argus_project_id = campaign.campaign_id
        return {"project_id": campaign.campaign_id}


@pytest_asyncio.fixture
async def setup(tmp_path):
    remote = Remote()
    client = OpenTrainingA2AClient(
        "https://training.example/a2a", transport=remote.transport
    )
    argus = Argus()
    store = CampaignStore(tmp_path)
    c = CampaignState(
        "campaign-1",
        "Bounded remote job",
        remote_task_id="task-1",
        argus_project_id="campaign-1",
    )
    store.create(c)
    service = Supervisor(store, client, argus)
    await service.discover()
    return service, remote, argus
