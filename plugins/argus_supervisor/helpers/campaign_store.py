"""Atomic campaign transactions and nonblocking cross-process authority locks."""

import fcntl
import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

from .models import CampaignState, SupervisorError
from .security import clean, identifier


class CampaignStore:
    def __init__(self, root):
        self.root = Path(root)
        for name in ("campaigns", "events", "leases", "state", "argus-home"):
            (self.root / name).mkdir(parents=True, exist_ok=True, mode=0o700)

    @contextmanager
    def lock(self, campaign_id="supervisor"):
        identifier(campaign_id)
        path = self.root / "state" / (campaign_id + ".lock")
        with path.open("a") as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise SupervisorError("campaign_busy") from None
            try:
                yield
            finally:
                fcntl.flock(handle, fcntl.LOCK_UN)

    def atomic(self, path, value):
        path = Path(path)
        fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".pending-")
        try:
            with os.fdopen(fd, "w") as handle:
                json.dump(value, handle, allow_nan=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def load(self, campaign_id):
        path = self.root / "campaigns" / (identifier(campaign_id) + ".json")
        try:
            value = json.loads(path.read_text())
            if (
                value.get("schema_version") != 1
                or value.get("campaign_id") != campaign_id
            ):
                raise ValueError()
            return CampaignState(**value)
        except FileNotFoundError:
            raise SupervisorError("campaign_not_found") from None
        except (ValueError, TypeError, AttributeError):
            raise SupervisorError("campaign_corrupt") from None

    def save(self, campaign):
        campaign.updated_at = time.time()
        self.atomic(
            self.root / "campaigns" / (identifier(campaign.campaign_id) + ".json"),
            campaign.to_dict(),
        )
        # Campaign is the authoritative transaction; leases are a diagnostic projection.
        self.atomic(
            self.root / "leases" / (campaign.campaign_id + ".json"),
            {
                "controller_id": campaign.controller_id,
                "epoch": campaign.controller_epoch,
                "expires_at": campaign.lease_expires_at,
                "mode": campaign.mode,
            },
        )

    def create(self, campaign):
        with self.lock(campaign.campaign_id):
            if (
                self.root / "campaigns" / (identifier(campaign.campaign_id) + ".json")
            ).exists():
                raise SupervisorError("campaign_exists")
            campaign.objective = clean(campaign.objective)
            self.save(campaign)

    def ids(self):
        return sorted(path.stem for path in (self.root / "campaigns").glob("*.json"))

    def append_event(self, campaign, event):
        if event["id"] in campaign.events:
            return False
        campaign.events[event["id"]] = {**clean(event), "delivery": "pending"}
        campaign.latest_significant_event = clean(event)
        # Deduplication and outbox are committed in the same campaign transaction.
        self.save(campaign)
        with (self.root / "events" / (campaign.campaign_id + ".jsonl")).open(
            "a"
        ) as handle:
            handle.write(json.dumps(clean(event)) + "\n")
            handle.flush()
            os.fsync(handle.fileno())
        return True
