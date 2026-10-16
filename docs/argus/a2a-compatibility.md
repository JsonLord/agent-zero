# OpenTraining compatibility and safe control

This is a client-side compatibility boundary, not an assertion about the currently
deployed OpenTraining. No OpenTraining implementation was changed.

Discovery tries `<A2A base>/.well-known/agent-card.json`, then `agent.json`, using
verified HTTPS, no redirects, finite timeouts and a 1 MiB response cap. A card must
have a name and skills array. Standard `message/send` (nonblocking), `tasks/get`
(history length zero) and artifacts are tentative until the remote accepts them.
Method-not-found marks the logical capability unavailable. Raw remote errors are
never surfaced; safe codes only. No capability is inferred from natural language.

Standard task identity is `result.id`; state is `result.status.state`. Compact
campaign metadata lives at `result.metadata.argus_supervisor`:
`revision`, `stage`, `run_id`, `attempt_id`, `source_sha`, `evidence_revision`,
`evidence_ref`, `blocked`. Ordinary metrics/stdout/history are ignored. Artifacts
are bounded data; file URLs are never followed automatically. A completed task is
an attempt outcome, never proof the entire mission was accepted.

To enable mutation the card must advertise this extension:

```json
{
  "uri": "urn:openoperator:campaign-control:v1",
  "params": {
    "lease_epoch_enforced": true,
    "operations": {
      "claim_control": "campaign/claim_control",
      "read_control": "campaign/read_control",
      "renew_control": "campaign/renew_control",
      "release_control": "campaign/release_control",
      "intervene": "campaign/intervene",
      "request_status": "campaign/request_status",
      "cancel": "tasks/cancel"
    }
  }
}
```

Each operation is optional and independently detected. Without read_control and
claim_control the client remains an observer. `read_control` is required beyond
the spec's logical operations because local state alone cannot prove authority.
`request_status` is needed to safely reconcile an ambiguous write; absence never
permits a retry. These are explicit missing remote prerequisites if the service
only implements generic Agent Zero A2A.

Lease objects contain `controller_id`, integer `epoch`, and Unix `expires_at`.
Claim receives campaign ID, controller ID, TTL and unique request ID. The remote
must serialize claims, change epochs monotonically on takeover, enforce expiry
and reject stale epochs on **every** mutation. Renewal/readback must agree.
Renew/release/intervene/cancel carry campaign ID, controller ID, controller epoch,
request ID and operation parameters. Cancellation targets the bound task only.

Submit uses `message/send` with `configuration.blocking=false`, a stable message
ID equal to the request ID, and
`metadata.argus_supervisor={campaign_id,controller_id,controller_epoch,request_id}`.
Optional project selection is also metadata and must be supported remotely.
A successful response must return a durable task ID promptly; no multi-hour
blocking request. Every logical mutation is single-shot locally. The remote must
provide persistent request-ID idempotency and readback if full ambiguous-write
recovery is to be qualified.

`campaign/request_status` receives campaign ID and original request ID. It returns
that exact request ID, `state=applied|not_applied`, and the durable task ID for an
applied submission. Readback clears ambiguity only, never automatically resends
or silently reacquires control. Live remote support is unverified until qualified.
