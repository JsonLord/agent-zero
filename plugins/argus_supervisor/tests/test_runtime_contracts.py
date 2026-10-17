"""Opt-in tests against the real isolated pinned packages, without live models."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from plugins.argus_supervisor.helpers.argus_bridge import ArgusBridge
from plugins.argus_supervisor.helpers.models import CampaignState

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.asyncio
async def test_real_argus_project_binding_survives_reopen(tmp_path):
    python = os.getenv("ARGUS_TEST_ARGUS_PYTHON")
    if not python:
        pytest.skip("isolated Argus runtime is not selected")
    home = tmp_path / "argus-home"
    campaign = CampaignState(
        "real-runtime-contract", "Observe a remote campaign; do not execute training"
    )
    first = ArgusBridge(home, python=python)
    result = await first.bind(campaign)
    assert result["project_id"] == campaign.campaign_id
    assert campaign.argus_project_id == campaign.campaign_id
    second = ArgusBridge(home, python=python)
    assert (await second.status(campaign))["project_id"] == campaign.campaign_id
    assert len(list((home / "projects").iterdir())) == 1
    assert not list(home.rglob("openoperator-turn-*"))  # no model turn for observation


def test_real_foreman_checks_and_policy_with_controlled_sdk_response():
    python = os.getenv("ARGUS_TEST_FOREMAN_PYTHON")
    if not python:
        pytest.skip("isolated Foreman runtime is not selected")
    worker = ROOT / "argus_supervisor/runtime/foreman_worker.py"
    # The module is actually evaluated in Foreman's isolated Python. Only the
    # network SDK response is controlled; observation/checks/policy are upstream.
    script = """import asyncio,importlib.util,json,sys
from unittest.mock import patch
from foreman.foreman.jev import JevForemanModel
spec=importlib.util.spec_from_file_location('worker',sys.argv[1])
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class Client:
 async def system_one(self,*,questions,**kwargs):
  return {key: 0.1 for key in questions}
 async def close(self): pass
request={'objective':'verify evidence only','run_id':'contract','state':'working','evidence':{'trust':'UNTRUSTED_REMOTE_DATA','data':{}}}
with patch.object(JevForemanModel,'_make_client',return_value=Client()):
 print(json.dumps(asyncio.run(m.assess(request))))
"""
    result = subprocess.run(
        [python, "-c", script, str(worker)],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, "isolated Foreman contract failed"
    assert json.loads(result.stdout)["directive"] in {
        "CONTINUE",
        "START_VERIFIER",
        "ESCALATE",
    }
