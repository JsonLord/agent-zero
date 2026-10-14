---
name: dspy-programming
description: Model task behavior as DSPy signatures/modules, set up the preinstalled isolated DSPy runtime, and build representative training/evaluation data for prompt optimization.
tags: [dspy, prompts, signatures, evaluation]
---

# DSPy Programming

DSPy is a programmatic system for language model tasks. Use `dspy.Signature`, `dspy.Predict`, and `dspy.Module` instead of blindly editing prompt strings.

## Environment

The preinstalled executable is `/opt/venv-dspy/bin/python`. It is not the system `python3` and does not inherit every package from `/opt/venv-a0`. Runtime pip is deliberately disabled for the serving venv; do not run ad-hoc installations to repair an experiment. Request a Docker build change if a reproducible dependency is missing.

```bash
/opt/venv-dspy/bin/python /a0/scripts/dspy_gepa.py preflight
```

`COMPATIBLE_API`, `COMPATIBLE_URL`, and `COMPATIBLE_MODEL` are server environment variables. Do not include their values in code, shell echo, logs, or data. For OpenAI-compatible providers DSPy uses `dspy.LM("openai/<model>", api_key=..., api_base=...)`. The helper normalizes this automatically.

## Dataset

The bundled experiment accepts JSONL with exactly one object per nonblank line and string `question` and `answer` fields. Use disjoint train, validation, and untouched holdout test sets; do not leak test examples into prompt evolution. Ensure examples reflect real usage and error classes. Exact-match is useful for labels, routing decisions, and fixed-format responses, not a valid universal metric for creative writing or open-ended reasoning.

## Safe small-start workflow

Start with `preflight`, inspect the data, then baseline/GEPA optimization using the `gepa-optimization` skill. Prefer deterministic task-specific metrics and qualitative feedback explaining failures. For free-form results, create and independently test an evaluator before increasing GEPA budget.

## References

- https://dspy.ai/3.4.0/getting-started/installation/
- https://dspy.ai/learn/optimization/optimizers/
