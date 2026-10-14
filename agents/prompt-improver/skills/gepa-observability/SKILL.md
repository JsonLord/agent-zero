---
name: gepa-observability
description: Observe GEPA optimization progress, candidate metric calls, reflection feedback, run logs, budgets, artifacts, and held-out regression results without exposing model credentials.
tags: [dspy, gepa, observation, experiments, tracing]
---

# GEPA Observability

An optimization is not successful merely because its process exists or its final file was written. Observe execution, score trends, errors, and comparison to baseline.

## Status without provider calls

```bash
/opt/venv-dspy/bin/python /a0/scripts/dspy_gepa.py inspect \
  --run-dir /a0/usr/workdir/optimizations/gepa-smoke-01
```

The offline command reads `status.json` plus a list of known artifact paths and never contacts a provider. A running job updates `metric_calls`, `last_score`, timestamps, and the execution phase. `events.log` contains library events; `gepa_logs/` holds optimizer details.

```bash
tail -n 60 /a0/usr/workdir/optimizations/gepa-smoke-01/events.log
ps -ef | grep '[d]spy_gepa.py'
```

The optimizer may write detailed traces containing example content, prompts, and model outputs. Restrict experiment directory access (umask 077) and do not share logs with untrusted recipients. Do not persist provider keys.

## Completion criteria

- `status=completed` and `optimized.json` exists.
- `validation.baseline`, `validation.optimized`, and `delta` are computed on identical validation examples.
- Prefer independent `holdout` metrics; without holdout, mark generalization unverified.
- Note metric calls, elapsed time, outcome of failures, and any provider quotas. Report regression rather than silently choosing a winning prompt.
- Do not claim full candidate-by-candidate visibility if a library version does not expose it: `metric_calls` track feedback invocations, while GEPA's log directory contains its own candidate traces.

## Recovery

If the process exits and status remains `running`, inspect the process, log and last update. Mark the run interrupted in your report; do not automatically restart a potentially costly GEPA search. Retry with a NEW run directory unless resumability is explicitly verified.

## References

- https://dspy.ai/3.3.0/api/optimizers/GEPA/overview/
- https://dspy.ai/3.1.2/api/optimizers/GEPA/GEPA_Advanced/
