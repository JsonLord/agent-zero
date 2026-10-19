# fasta2a_server.py DOX

## Purpose

- Own the `fasta2a_server.py` helper module.
- This module serves Agent Zero through a dynamic A2A proxy.
- Keep this file-level DOX profile synchronized with `fasta2a_server.py` because this directory is intentionally flat.

## Ownership

- `fasta2a_server.py` owns the runtime implementation.
- `fasta2a_server.py.dox.md` owns durable notes about responsibilities, contracts, side effects, and verification for that implementation.
- Classes:
- `AgentZeroFastA2A` (`FastA2A`)
  - `async _agent_card_endpoint(self, request: Request) -> StarletteResponse`
- `AgentZeroWorker` (`Worker`)
  - `async run_task(self, params: Any) -> None`
  - `async cancel_task(self, params: Any) -> None`
  - `build_message_history(self, history: List[Any]) -> List[Message]`
  - `build_artifacts(self, result: Any) -> List[Artifact]`
- `DynamicA2AProxy` (no explicit base class)
  - `get_instance()`
  - `reconfigure(self, token: str)`
- Top-level functions:
- `_finalize_agent_card(agent_card_body: bytes) -> bytes`: Set accurate transport capabilities and public identity.
- `is_available()`: Check if FastA2A is available and properly configured.
- `get_proxy()`: Get the FastA2A proxy instance.
- Notable constants/configuration names: `_PRINTER`.

## Runtime Contracts

- Helper modules own reusable framework APIs and must preserve public callers unless all callers, tests, and docs are updated together.
- Update this file whenever public functions, classes, persistence behavior, path/security assumptions, side effects, or cross-module contracts change.
- Agent Zero wraps `FastA2A` with `AgentZeroFastA2A` so the generated agent card sets `capabilities.streaming` to `false` because the pinned transport does not implement streaming.
- Observed side-effect areas: filesystem writes, filesystem deletion, settings/state persistence, secret handling, scheduler state.
- Imported dependency areas include: `agent`, `asyncio`, `atexit`, `contextlib`, `helpers`, `helpers.persist_chat`, `helpers.print_style`, `initialize`, `json`, `starlette.requests`, `starlette.responses`, `threading`, `typing`, `uuid`.

## Key Concepts

- Important called helpers/classes observed in the source: `PrintStyle`, `DynamicA2AProxy.get_instance`, `json.loads`, `json.dumps`, `super.__init__`, `super._agent_card_endpoint`, `join`, `UserMessage`, `threading.Lock`, `atexit.register`, `self._configure`, `settings.get_settings`, `path.startswith`, `self._convert_message`, `initialize_agent`, `AgentContext`, `context.log.log`, `context.communicate`, `context.reset`, `AgentContext.remove`, `remove_chat`, `self.storage.update_task`, `self._register_shutdown`.
- Keep request/response, tool, or helper semantics documented here at the same time as source changes.

## Work Guidance

- Preserve public helper APIs used by core code and plugins unless every caller is updated.
- Keep path, auth, secret, persistence, network, and subprocess behavior explicit and bounded.
- Prefer adding cohesive helper functions here only when behavior is reused across modules.

## Verification

- Run targeted tests for changed helper behavior; run security regressions for auth, filesystem, WebSocket, tunnel, upload, or secret-handling helpers.
- Related tests:
  - `tests/test_fasta2a_server.py`

## Child DOX Index

No child DOX files.

## OpenTraining boundary hardening

- Generated settings token remains the sole credential authority; blank authority is 503.
- Bearer/X-API-KEY headers and legacy token/project paths authenticate before worker startup.
  Query-string credentials are no longer accepted. Constant-time comparisons avoid timing disclosure.
- Mounted ASGI path/root_path normalization reaches internal `/`; lifecycle startup is serialized.
- Pydantic protocol validation is mapped to bounded JSON-RPC HTTP 400 at the RPC endpoint.
- Both card discovery aliases share one serializer. Only general assistance is advertised;
  streaming is false because FastA2A 0.5 does not implement it. Public URL/docs come from
  validated A0_PUBLIC_URL, HF SPACE_HOST/SPACE_ID, or the dedicated HF fallback.
- Tests: tests/test_opentraining_a2a.py exercises real pinned ASGI, broker/storage and worker.
