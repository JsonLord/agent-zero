# Argus Supervisor Profile

## Purpose and Ownership
Human-facing facade for `plugins/argus_supervisor`; not a replacement for Argus.
Own role/specifics and the argus-supervision skill. The plugin owns durable state,
authority and execution. Training stays remote through OpenTraining.

## Contracts and Verification
Only expose Needs you, attempt outcomes, stage transitions, Reviewer verdicts,
mission completion and critical control/infrastructure failures. Never claim a
lease, task, model turn or acceptance succeeded without durable evidence.
Verify discovery with `helpers.subagents.get_available_agents_dict(None)` and run
the supervisor integration tests. Never include credentials in task text.
