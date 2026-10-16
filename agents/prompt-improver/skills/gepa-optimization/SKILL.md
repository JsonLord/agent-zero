---
name: gepa-optimization
description: Build, budget, execute, and compare DSPy GEPA reflective prompt optimization runs with separated train/validation/test data and safe OpenAI-compatible provider configuration.
tags: [dspy, gepa, prompt-evolution, benchmark]
---

# GEPA Optimization

GEPA evolves instructions through feedback rather than updating LLM weights. It uses a student model for evaluation, a reflection model to propose improvements, and an explicit metric. Set realistic objectives, budget, and holdout before starting.

## Preflight

```bash
/opt/venv-dspy/bin/python /a0/scripts/dspy_gepa.py preflight
```

The script requires `COMPATIBLE_API`, `COMPATIBLE_URL`, `COMPATIBLE_MODEL` for real runs. Separate `DSPY_REFLECTION_MODEL` is optional; default is the configured model. Never print the secret. An authenticated inference request is **not** part of preflight; a real optimization is the provider connectivity test.

## Minimal optimization

Create train/val/test files using the `question`/`answer` JSONL contract, then:

```bash
umask 077
/opt/venv-dspy/bin/python /a0/scripts/dspy_gepa.py optimize \
  --train /a0/usr/workdir/datasets/train.jsonl \
  --val /a0/usr/workdir/datasets/val.jsonl \
  --test /a0/usr/workdir/datasets/test.jsonl \
  --run-dir /a0/usr/workdir/optimizations/gepa-smoke-01 \
  --auto light --num-threads 1
```

Choose exactly one GEPA budget: `--auto light|medium|heavy` or `--max-metric-calls N`. Start with light on an external model; larger budgets and parallelism require an explicit cost discussion.

The provided general-purpose benchmark deliberately uses normalized exact match. Use it for constrained outputs; do **not** use it to optimize creative quality, open answers, nuanced safety, or multi-step agent behavior. For those, develop a specialized program and GEPA feedback metric modeled on the official examples.

## Evidence

Require baseline and optimized validation scores, independent holdout scores when provided, completed run status, and a saved `optimized.json` DSPy artifact. Inspect the `events.log` and `gepa_logs/` for debugging. Optimization may run for many API calls; a non-zero or timed-out run is not PASS.

Only propose promotion to production when holdout and regression checks support it. Keep previous prompts for rollback.

## References

- https://dspy.ai/learn/optimization/optimizers/
- https://dspy.ai/3.3.0/api/optimizers/GEPA/overview/
- https://dspy.ai/3.4.0/tutorials/gepa_facilitysupportanalyzer/
