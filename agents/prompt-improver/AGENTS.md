# Prompt Improver Profile

A native OpenOperator specialist for reproducible DSPy prompt optimization.

- Parent code lives at `agents/prompt-improver/`; runnable CLI: `scripts/dspy_gepa.py`.
- Skills: `dspy-programming`, `gepa-optimization`, and `gepa-observability`.
- Keep optimization data, candidates, and reports under `/a0/usr/workdir/optimizations/<run-id>`; no credentials or raw private input data in status summaries.
- Inspect, benchmark, and propose prompt changes autonomously. Promotion into production agent prompts, deployment, and substantial optimization spending require explicit authorization.
- The installed DSPy runtime is deliberately isolated at `/opt/venv-dspy`, not the Agent Zero service venv.
