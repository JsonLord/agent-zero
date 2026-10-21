"""Credential-free integration discovery shared by ASGI and WSGI entrypoints."""

from pathlib import Path


def bootstrap_links() -> dict:
    return {
        "docs": "/docs",
        "apiDocs": "/api-docs",
        "a2a": {
            "base": "/a2a/",
            "agentCard": "/a2a/.well-known/agent.json",
            "contract": "/docs/a2a.json",
        },
    }


def a2a_contract() -> dict:
    return {
        "service": "OpenOperator",
        "a2a": {
            "basePath": "/a2a/",
            "agentCard": "/a2a/.well-known/agent.json",
            "agentCardCompatibility": "/a2a/.well-known/agent-card.json",
            "rpcEndpoint": "/a2a/",
            "protocolVersion": "0.2.5",
            "transport": "JSON-RPC",
            "auth": ["Authorization: Bearer", "X-API-KEY"],
            "methods": ["message/send", "tasks/get", "tasks/cancel"],
            "wireCase": "camelCase",
        },
        "argusSupervisor": {
            "extension": "urn:openoperator:argus-supervisor:v1",
            "readOperations": [
                "supervisor.health",
                "supervisor.status",
                "campaign.list",
            ],
            "mutationOperationsQualified": False,
        },
    }


def integration_docs() -> str:
    return (Path(__file__).resolve().parents[1] / "docs/openoperator-a2a.md").read_text(
        encoding="utf-8"
    )
