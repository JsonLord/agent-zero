# Argus Supervisor

## Purpose and Ownership
Own durable campaign supervision over remote OpenTraining A2A. `helpers/` owns
transport, state, reducer, leases and orchestration; `runtime/` runs only inside
the pinned isolated Argus/Foreman environments. API classes inherit normal auth
and CSRF. Extensions reuse startup_migration/job_loop; no scheduler replacement.

## Local Contracts
The user explicitly requires `plugins/argus_supervisor`, an exception to the
parent's underscore naming convention. Manifest discovery supports this name.
Argus owns campaign decisions. Foreman is advisory and receives no remote client
or credentials. All training remains remote. No runtime installs, listeners,
secret persistence, direct model-generated authority, or automatic mutation retry.
Campaign file locks serialize API/heartbeat transitions across threads/processes.
Write mutation intent before sending; unresolved intent blocks replay after crash.
Remote authoritative readback and matching unexpired epoch gate every mutation.
The job loop never writes chat messages; status APIs expose a strict event allowlist.

## Verification
Run `python -m pytest plugins/argus_supervisor/tests` in the framework environment.
Pinned runtime contract tests use separate venvs, no provider keys. Live qualification
must distinguish transport denial, missing capability and successful remote execution.
