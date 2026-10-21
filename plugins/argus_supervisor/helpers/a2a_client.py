"""Bounded A2A JSON-RPC adapter. No blocking training requests or blind retries."""

import asyncio
import json
import time
import uuid

import aiohttp

from .models import AmbiguousMutation, SupervisorError, Unsupported
from .security import clean, endpoint, evidence_envelope

POLICY = {
    "execution": "remote-only",
    "publication": False,
    "destructive_git": False,
    "credential_changes": False,
    "force_push": False,
    "merge": False,
}

EXTENSION = "urn:openoperator:campaign-control:v1"
EXT_METHODS = {
    name: "campaign/" + name
    for name in (
        "claim_control",
        "renew_control",
        "release_control",
        "read_control",
        "intervene",
        "request_status",
    )
}
MUTATIONS = {"submit", "renew_control", "release_control", "intervene", "cancel"}


class OpenTrainingA2AClient:
    def __init__(self, url, token="", project=None, *, timeout=15, transport=None):
        self.url = endpoint(url)
        self._token = token
        self.project = project
        self.timeout = min(30, max(1, timeout))
        self.transport = transport
        self.capabilities = {}

    async def _request(self, method, suffix="", payload=None, *, mutation=False):
        try:
            if self.transport:
                return await self.transport(method, suffix, payload)
            headers = {"Accept": "application/json"}
            if self._token:
                headers.update(
                    Authorization="Bearer " + self._token, **{"X-API-KEY": self._token}
                )
            async with (
                aiohttp.ClientSession(
                    timeout=aiohttp.ClientTimeout(total=self.timeout, connect=3),
                    trust_env=True,
                    headers=headers,
                ) as session,
                session.request(
                    method, self.url + suffix, json=payload, allow_redirects=False
                ) as response,
            ):
                if response.status != 200:
                    # A gateway error may follow a committed remote write.
                    if mutation:
                        raise AmbiguousMutation("mutation_outcome_unknown")
                    raise SupervisorError(f"remote_http_{response.status}")
                body = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    body.extend(chunk)
                    if len(body) > 1024 * 1024:
                        raise ValueError()
                result = json.loads(body)
                if not isinstance(result, dict):
                    raise TypeError()
                return result
        except asyncio.CancelledError:
            raise
        except (aiohttp.ClientError, TimeoutError, OSError, ValueError, TypeError):
            if mutation:
                raise AmbiguousMutation("mutation_outcome_unknown") from None
            raise SupervisorError("remote_transport_or_payload_error") from None

    async def discover(self):
        self.capabilities = {}
        card = None
        for suffix in ("/.well-known/agent-card.json", "/.well-known/agent.json"):
            try:
                card = await self._request("GET", suffix)
                break
            except SupervisorError:
                continue
        if (
            not isinstance(card, dict)
            or not isinstance(card.get("skills"), list)
            or not card.get("name")
        ):
            raise SupervisorError("invalid_agent_card")
        # Standard A2A operations are tentative until called; never infer leases
        # from skill prose or natural-language claims.
        self.capabilities = {
            "discover": True,
            "status": "tasks/get",
            "evidence": "tasks/get",
            "submit": "message/send",
            "cancel": False,
        }
        capabilities = card.get("capabilities", {})
        extensions = (
            capabilities.get("extensions", []) if isinstance(capabilities, dict) else []
        )
        for extension in extensions if isinstance(extensions, list) else []:
            if not isinstance(extension, dict) or extension.get("uri") != EXTENSION:
                continue
            params = extension.get("params", {})
            if (
                not isinstance(params, dict)
                or params.get("lease_epoch_enforced") is not True
                or params.get("policy_enforced") is not True
            ):
                continue
            operations = params.get("operations", {})
            if not isinstance(operations, dict):
                continue
            for logical, method in EXT_METHODS.items():
                if operations.get(logical) == method:
                    self.capabilities[logical] = method
            if operations.get("cancel") == "tasks/cancel":
                self.capabilities["cancel"] = "tasks/cancel"
        return {
            name: bool(self.capabilities.get(name))
            for name in (
                "discover",
                "submit",
                "status",
                "evidence",
                *EXT_METHODS,
                "cancel",
            )
        }

    async def rpc(self, operation, params, *, mutation=False):
        method = self.capabilities.get(operation)
        if not method:
            raise Unsupported("unsupported_" + operation)
        rpc_id = str(uuid.uuid4())
        response = await self._request(
            "POST",
            "/",  # Canonical JSON-RPC mount root; discovery uses URL suffixes.
            payload={
                "jsonrpc": "2.0",
                "id": rpc_id,
                "method": method,
                "params": params,
            },
            mutation=mutation,
        )
        if (
            not isinstance(response, dict)
            or response.get("id") != rpc_id
            or response.get("jsonrpc") != "2.0"
        ):
            if mutation:
                raise AmbiguousMutation("mutation_outcome_unknown")
            raise SupervisorError("invalid_remote_result")
        if response.get("error"):
            error = response["error"]
            if isinstance(error, dict) and error.get("code") == -32601:
                self.capabilities[operation] = False
                raise Unsupported("unsupported_" + operation)
            if mutation:
                raise AmbiguousMutation("mutation_rejected_readback_required")
            raise SupervisorError("remote_rpc_error")
        if not isinstance(response.get("result"), dict):
            if mutation:
                raise AmbiguousMutation("mutation_outcome_unknown")
            raise SupervisorError("invalid_remote_result")
        return response["result"]

    async def status(self, task_id):
        result = await self.rpc("status", {"id": task_id, "history_length": 0})
        if result.get("id") != task_id:
            raise SupervisorError("remote_task_identity_mismatch")
        status = result.get("status", {})
        raw_metadata = result.get("metadata") or {}
        if not isinstance(raw_metadata, dict):
            raise SupervisorError("invalid_task_metadata")
        metadata = raw_metadata.get("argus_supervisor", {})
        if (
            not isinstance(status, dict)
            or not isinstance(metadata, dict)
            or not isinstance(status.get("state"), str)
        ):
            raise SupervisorError("invalid_task_status")
        # Do not persist stdout, history, arbitrary metrics or transcript.
        return clean(
            {
                "task_id": task_id,
                "state": status["state"],
                **{
                    key: metadata.get(key)
                    for key in (
                        "revision",
                        "stage",
                        "run_id",
                        "attempt_id",
                        "source_sha",
                        "evidence_revision",
                        "heartbeat_seq",
                        "evidence_ref",
                        "blocked",
                        "mission_completed",
                    )
                },
            }
        )

    async def evidence(self, task_id):
        result = await self.rpc("evidence", {"id": task_id, "history_length": 0})
        if result.get("id") != task_id:
            raise SupervisorError("remote_task_identity_mismatch")
        return evidence_envelope(
            {
                "artifacts": result.get("artifacts", []),
                "status": result.get("status", {}),
            }
        )

    async def read_control(self, campaign_id):
        return await self.rpc("read_control", {"campaign_id": campaign_id})

    async def claim_control(self, campaign_id, controller_id, ttl, request_id):
        return await self.rpc(
            "claim_control",
            {
                "campaign_id": campaign_id,
                "controller_id": controller_id,
                "ttl_seconds": ttl,
                "constraints": POLICY,
                "request_id": request_id,
            },
            mutation=True,
        )

    async def mutate(self, operation, campaign_id, lease, request_id, **params):
        if operation not in MUTATIONS:
            raise Unsupported("unsupported_mutation")
        from .lease import verify

        remote = await self.read_control(campaign_id)
        verify(lease, remote, now=time.time())
        authority = {
            "campaign_id": campaign_id,
            "controller_id": lease["controller_id"],
            "controller_epoch": lease["epoch"],
            "constraints": POLICY,
            "request_id": request_id,
        }
        # Authority is outside untrusted task text. The remote must enforce it.
        if operation == "submit":
            text = params.pop("text", "")
            message = {
                "kind": "message",
                "role": "user",
                "message_id": request_id,
                "parts": [{"kind": "text", "text": text}],
            }
            if self.project:
                authority["project"] = self.project
            params = {
                "message": message,
                "configuration": {
                    "blocking": False,
                    "accepted_output_modes": ["application/json", "text/plain"],
                },
                "metadata": {"argus_supervisor": authority},
            }
        else:
            params = {**params, **authority}
        return await self.rpc(operation, params, mutation=True)
