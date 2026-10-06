### goal
Manage the durable execution contract for this context.

Actions:
- `get`: inspect compact state.
- `create`: set objective plus optional title, criteria, constraints, evidence, autonomy, and token budget.
- `checkpoint`: record a meaningful milestone/evidence/attention transition.
- `revise`: preserve the old definition and revise the contract.
- `subgoal`: delegate one bounded child outcome to an existing profile in a fresh context; declare dependencies and keep parallel writers isolated.
- `complete`: evaluate all criteria; NOT VERIFIED is never PASS.
- `blocked`: use only after viable alternatives fail; include an attention reason.

Do not checkpoint every command. While active, continue autonomously without routine narration. Permissions and approval gates remain authoritative at every autonomy level.
