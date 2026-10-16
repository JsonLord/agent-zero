"""Remote readback is authoritative; a journal alone never grants authority."""

import math
import time

from .models import SupervisorError


def valid(lease, now=None):
    now = time.time() if now is None else now
    return (
        isinstance(lease, dict)
        and isinstance(lease.get("controller_id"), str)
        and bool(lease["controller_id"])
        and type(lease.get("epoch")) is int
        and lease["epoch"] >= 0
        and type(lease.get("expires_at")) in (float, int)
        and math.isfinite(lease["expires_at"])
        and lease["expires_at"] > now
    )


def verify(local, remote, *, now=None):
    if not valid(local, now) or not valid(remote, now):
        raise SupervisorError("lease_expired_or_missing")
    if any(local[key] != remote[key] for key in ("controller_id", "epoch")):
        raise SupervisorError("stale_controller_epoch")


def lose(campaign):
    changed = campaign.mode == "controller"
    campaign.mode = "observer"
    campaign.lease_expires_at = None
    return changed


def snapshot(campaign):
    return {
        "controller_id": campaign.controller_id,
        "epoch": campaign.controller_epoch,
        "expires_at": campaign.lease_expires_at,
    }


def accept(campaign, remote, controller_id):
    if not valid(remote) or remote["controller_id"] != controller_id:
        raise SupervisorError("remote_control_not_owned")
    if (
        campaign.controller_epoch is not None
        and remote["epoch"] < campaign.controller_epoch
    ):
        raise SupervisorError("stale_controller_epoch")
    campaign.controller_id = remote["controller_id"]
    campaign.controller_epoch = remote["epoch"]
    campaign.lease_expires_at = remote["expires_at"]
    campaign.mode = "controller"
