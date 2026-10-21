# Clean OpenOperator source reconstruction

Clean parent: `1cd0489b8a5236bc1aaafbf7de01a93842d71896`.
Branch: `jules/openoperator-a2a-clean-production`.

The implementation is reconstructed from reviewed file contents, not merged or
cherry-picked history. PR #31 must not be merged. PR #32 is separate OpenTraining
work and is untouched. Incoming API/MCP/A2A authority is unchanged. No Argus
controller/mutation authority or new listener is added.

## Comparison evidence

The user reports that the full read-only OpenOperator → Spynel → argus-supervisor →
existing OpenTrainingA2AClient → OpenTraining tasks/get → persisted observer →
response chain already passed live qualification. This task does not relabel local
mocked tests as a new live qualification.

The GitHub comparison tree is `1b6017a395dfa7c0857bf5431d7c33a2eccd1cc7`.
The public Space was independently read at HF snapshot revision
`35437d7b352e6e7c47ebc1d7b0364e2e1c464ad4`. Both its build manifest and live `/health`
report source `5446faae1f0bbee5cd0a1fc3b5a5d83fe4ab6b0c`; GitHub does not serve that
commit. It must not be confused with the HF repository revision.

The snapshot differs from the GitHub reference in 328 paths: 322 omitted non-source
assets/markers, generated `.gitattributes` and build manifest, and whitespace changes
in two runtime modules, one test and the A2A Markdown. All changed shared Python
files have identical ASTs. No missing Python/shell/JS/HTML/config source was found.
These deployment-packaging differences are recorded, not imported into product Git.
The new source retains the clean base's assets.

## Intentional differences

- Agent cards use one complete registry keyed by skill ID before serialization;
  disabled mode has general assistance only, enabled mode adds the three read skills,
  and campaign_control and fabricated/duplicate skills are removed.
- Register the compatibility card route inside FastA2A's actual router.
- Keep bounded HTTP400 / JSON-RPC -32600 validation while removing unused pre-parsing.
- Handle malformed extension metadata with bounded errors. Use canonical health
  enablement instead of overriding its result. Do not echo unknown operation text.
- `/docs` uses Starlette's response class; the reference incorrectly passes ASGI
  arguments to Flask's Response. Discovery links and contract otherwise match.
- Add the installed Argus profile to the dedicated HF inventory. This does not enable
  Argus or require a model backend.
- Retain the clean base's real discovery test instead of the reference's unconditional
  skip. Add actual ASGI serialization/auth/RPC tests, an explicit CI no-skip gate, and
  the fonttools dependency needed by the existing icon test.
- Qualification tooling now performs bounded assertions without raw authenticated
  output. Paired helper contracts and this source-parity report are updated.

Every other runtime file is byte-identical to the GitHub comparison tree, including
Spynel, observer persistence/reducer, lease logic, Argus/Foreman
bridges, incoming settings/authentication authority and the HF entrypoint diagnostics.
The existing streaming advertisement is retained for parity; it is not newly qualified.

Machine-readable evidence: [clean-source-parity.json](clean-source-parity.json).
There are no unexplained runtime-code differences. Qualified behavior tree parity
passes for the read-only chain; broad historical requalification is unnecessary.
A new exact-SHA deployment still requires fresh CI and the prescribed narrow smoke.

## Validation and deployment gates

Use `/workspace/venvs/openoperator/bin/python` for framework checks and isolated pinned
Argus/Foreman interpreters for upstream runtime contracts. Real discovery must execute;
CI checks the JUnit testcase has neither skip, failure nor error. The full selected
suite and final results are recorded in the new PR and local JUnit results, never
borrowed from PR #31.

Compile `helpers` and `plugins/argus_supervisor`, syntax-check the qualification and
entrypoint scripts, and run `git diff --check`. Scan both current source and the
new commit delta for exposed/provider credentials; report counts only. Scratch probes,
logs, raw responses and unsafe ancestry are excluded.

Deployment is conditional on clean ancestry, explained tree parity and new-head CI
success. Use `scripts/deploy_hf_space.py --sha <full-clean-sha> --space
Leon4gr45/openoperator --verify`; the tool rejects dirty state and records exact source
provenance. A push alone is not deployment verification. Do not deploy OpenTraining,
change its secrets or acquire any controller as part of this work.

## Live deployment follow-up: WSGI discovery fallback

The first clean deployment reported its exact SHA and passed all three deterministic
Argus reads. Both external and loopback requests returned 404 for `/docs` and
`/docs/a2a.json`, with health using the existing Flask fallback response. ASGI-only
coverage missed this serving path. The follow-up adds discovery to the existing
Flask registration and shares pure links/contract/Markdown functions with ASGI.
Protected auth/CSRF and all observer/controller behavior remain unchanged. The real
Flask regression reproduces the previously missing routes. This is an explained
transport-coverage correction rather than a controller or observer redesign.

The rebuild also demonstrated ephemeral observer storage: one campaign before
rebuild, zero afterward. Operator-managed persistent storage remains separate work.
During the initial credential probe, no harmless new A2A task was accepted:
OpenTraining RPC returned 401 with the supplied credential. Creating a fresh test task
and attaching its observer requires the current valid OpenTraining token. No controller
or training job has been started by these tests. Never substitute exposed credentials.

The live RPC probe also returned HTTP405 on the bare base path. The same production
OpenTrainingA2AClient now supplies `/` when posting its JSON-RPC envelope, preserving
well-known discovery suffixes and enforcing the documented `/a2a/` mount contract.
A real loopback HTTP regression rejects `/a2a` and accepts only `/a2a/`. This one
call-site correction is an intentional, explained runtime difference; the client is
not replaced, and credential/method/controller validation is unchanged. That historical HTTP401 was resolved by the operator updating the secure credential.
Two harmless tasks later completed and bounded concurrent status reads passed.
Initial model/task execution latency is separate from observer transport latency;
no performance redesign is part of this correction.


## Observer execution contract correction

The backend already supports local observer creation and one tasks/get poll without
a controller epoch, lease extension, Argus backend or Foreman. Live delegation
over-applied the mutation guard and refused observer attachment. Only the profile
specifics and both semantically aligned skills change execution instructions:
explicit authority matrix, exact create/observe/readback path, and prohibition on
inventing epoch errors or persistence. Backend service, leases, authority checks,
transport and incoming authentication are unchanged. Mission binding remains
separate; remote submit/intervene/cancel/release still require controller authority.

Deterministic service and real authenticated/CSRF-protected plugin API regressions
use the production client with controlled transport, without lease capabilities.
They require exactly one tasks/get, persisted completed state and last_seen, no
claim/read_control/mutate/authority calls, and no model backend calls. Negative
mutation cases retain stable stale_controller_epoch failure. Live acceptance must
independently find the requested observer in production storage; model response
or dispatcher completion alone does not qualify the chain.
