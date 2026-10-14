#!/usr/bin/env python3
"""Offline inspection and controlled GEPA optimization using Space-compatible LM secrets.

Requires DSPy only for optimize. All run output stays under an explicit run directory.
Sample JSONL rows: {"question": "Classify ...", "answer": "complaint"}.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.metadata
import json
import logging
import os
from pathlib import Path
import sys
import threading
import time
from typing import Any


def timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def atomic_json(path: Path, payload: dict[str, Any]) -> None:
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def update_status(run_dir: Path, **fields: Any) -> dict[str, Any]:
    status_file = run_dir / "status.json"
    status = read_json(status_file)
    status.update(fields)
    status["updated_at"] = timestamp()
    atomic_json(status_file, status)
    return status


def normalize(value: Any) -> str:
    return " ".join(str(value or "").casefold().split())


def load_rows(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not path.is_file():
        raise ValueError(f"Dataset not found: {path}")
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict) or not isinstance(item.get("question"), str) or not isinstance(item.get("answer"), str):
            raise ValueError(f"{path}:{lineno}: expected string question and answer")
        if not item["question"].strip():
            raise ValueError(f"{path}:{lineno}: question must not be empty")
        rows.append({"question": item["question"], "answer": item["answer"]})
    if not rows:
        raise ValueError(f"Dataset is empty: {path}")
    return rows


def assert_disjoint(train: list[dict[str, str]], val: list[dict[str, str]], test: list[dict[str, str]]) -> None:
    sets = [set(normalize(row["question"]) for row in rows) for rows in (train, val, test)]
    if sets[0] & sets[1] or sets[0] & sets[2] or sets[1] & sets[2]:
        raise ValueError("Dataset leakage: questions overlap train, val, or holdout test")


def score_answer(expected: str, actual: str, metric: str) -> float:
    exp, got = normalize(expected), normalize(actual)
    if metric == "exact":
        return float(exp == got)
    if metric == "contains":
        return float(bool(exp) and exp in got)
    raise ValueError(f"Unsupported metric: {metric}")


def dspy_model_name(name: str) -> str:
    # COMPATIBLE_MODEL is the endpoint's native model ID, not a DSPy provider ID.
    return name if name.startswith("openai/") else "openai/" + name


def preflight() -> int:
    keys = ("COMPATIBLE_API", "COMPATIBLE_URL", "COMPATIBLE_MODEL")
    try:
        version = importlib.metadata.version("dspy")
    except importlib.metadata.PackageNotFoundError:
        version = None
    result = {
        "status": "ready" if version and all(os.environ.get(k) for k in keys) else "blocked",
        "dspy_version": version,
        "python": sys.version.split()[0],
        "secrets_present": {key: bool(os.environ.get(key)) for key in keys},
        "reflection_model_configured": bool(os.environ.get("DSPY_REFLECTION_MODEL")),
        "default_threads": 1,
        "note": "This preflight is offline and does not verify provider inference.",
    }
    print(json.dumps(result, indent=2))
    return 0 if result["status"] == "ready" else 2


def inspect(run_dir: Path) -> int:
    status = read_json(run_dir / "status.json")
    if not status:
        print(json.dumps({"status": "missing", "run_dir": str(run_dir)}))
        return 2
    paths = ["optimized.json", "events.log", "gepa_logs"]
    status["artifacts"] = {p: (run_dir / p).exists() for p in paths}
    print(json.dumps(status, indent=2, sort_keys=True))
    return 0 if status.get("state") == "completed" else 2


def evaluate(program: Any, examples: list[Any], metric_name: str) -> dict[str, Any]:
    correct = 0.0
    for example in examples:
        output = program(question=example.question)
        correct += score_answer(example.answer, getattr(output, "answer", ""), metric_name)
    return {"score": round(correct / len(examples), 6), "examples": len(examples)}


class MetricMonitor:
    """GEPA feedback metric; store aggregate progress, not example text or credentials."""

    def __init__(self, dspy: Any, run_dir: Path, metric_name: str):
        self.dspy = dspy
        self.run_dir = run_dir
        self.metric_name = metric_name
        self.count = 0
        self.lock = threading.Lock()

    def __call__(self, example: Any, pred: Any, trace: Any = None) -> Any:
        actual = str(getattr(pred, "answer", "") or "")
        expected = str(example.answer)
        score = score_answer(expected, actual, self.metric_name)
        feedback = (
            "Matches the expected task output."
            if score == 1.0 else
            "Does not satisfy the reference output. Expected: " + expected[:200] +
            "; received: " + actual[:200] +
            ". Improve task instructions and consistent output format."
        )
        with self.lock:
            self.count += 1
            update_status(self.run_dir, metric_calls=self.count, last_score=score, phase="gepa")
        return self.dspy.Prediction(score=score, feedback=feedback)


def _make_lm(dspy: Any, model: str, url: str, key: str, *, reflection: bool) -> Any:
    return dspy.LM(
        dspy_model_name(model),
        api_base=url,
        api_key=key,
        temperature=0.7 if reflection else 0.0,
        max_tokens=2048 if reflection else 512,
    )


def optimize(args: argparse.Namespace) -> int:
    # Validate dataset and environment before making any provider requests.
    train_rows = load_rows(args.train)
    val_rows = load_rows(args.val)
    test_rows = load_rows(args.test) if args.test else []
    assert_disjoint(train_rows, val_rows, test_rows)
    values = {k: os.environ.get(k, "").strip() for k in ("COMPATIBLE_API", "COMPATIBLE_URL", "COMPATIBLE_MODEL")}
    missing = [key for key, value in values.items() if not value]
    if missing:
        raise RuntimeError("Missing required Space environment variables: " + ", ".join(missing))
    if args.num_threads < 1 or args.num_threads > 8:
        raise ValueError("num-threads must be within 1..8")
    if args.max_metric_calls is not None and args.max_metric_calls < 1:
        raise ValueError("max-metric-calls must be positive")
    if args.run_dir.exists():
        raise FileExistsError(f"Run directory already exists: {args.run_dir}. Use a new run ID.")
    old_umask = os.umask(0o077)
    try:
        args.run_dir.mkdir(parents=True, exist_ok=False)
    finally:
        os.umask(old_umask)
    started = time.monotonic()
    update_status(
        args.run_dir, state="running", phase="initializing", started_at=timestamp(),
        pid=os.getpid(), metric=args.metric, train_examples=len(train_rows),
        validation_examples=len(val_rows), test_examples=len(test_rows),
        metric_calls=0, budget=args.auto if args.max_metric_calls is None else args.max_metric_calls,
        num_threads=args.num_threads,
    )
    try:
        import dspy

        logger = logging.getLogger("dspy")
        logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(args.run_dir / "events.log", encoding="utf-8")
        logger.addHandler(file_handler)
        try:
            student_lm = _make_lm(dspy, values["COMPATIBLE_MODEL"], values["COMPATIBLE_URL"], values["COMPATIBLE_API"], reflection=False)
            reflection_lm = _make_lm(
                dspy,
                os.environ.get("DSPY_REFLECTION_MODEL") or values["COMPATIBLE_MODEL"],
                os.environ.get("DSPY_REFLECTION_URL") or values["COMPATIBLE_URL"],
                os.environ.get("DSPY_REFLECTION_API") or values["COMPATIBLE_API"],
                reflection=True,
            )
            dspy.configure(lm=student_lm)
            trainset = [dspy.Example(**row).with_inputs("question") for row in train_rows]
            valset = [dspy.Example(**row).with_inputs("question") for row in val_rows]
            testset = [dspy.Example(**row).with_inputs("question") for row in test_rows]
            baseline = dspy.Predict("question -> answer")
            update_status(args.run_dir, phase="baseline")
            baseline_validation = evaluate(baseline, valset, args.metric)
            update_status(args.run_dir, phase="gepa", baseline_validation=baseline_validation)
            monitor = MetricMonitor(dspy, args.run_dir, args.metric)
            kwargs: dict[str, Any] = {
                "metric": monitor,
                "reflection_lm": reflection_lm,
                "log_dir": str(args.run_dir / "gepa_logs"),
                "num_threads": args.num_threads,
                "track_stats": True,
                "track_best_outputs": True,
                "use_merge": False,
            }
            if args.max_metric_calls is None:
                kwargs["auto"] = args.auto
            else:
                kwargs["max_metric_calls"] = args.max_metric_calls
            optimizer = dspy.GEPA(**kwargs)
            optimized = optimizer.compile(student=baseline, trainset=trainset, valset=valset)
            optimized.save(str(args.run_dir / "optimized.json"))
            update_status(args.run_dir, phase="validation")
            optimized_validation = evaluate(optimized, valset, args.metric)
            holdout = None
            if testset:
                update_status(args.run_dir, phase="holdout")
                holdout = {
                    "baseline": evaluate(baseline, testset, args.metric),
                    "optimized": evaluate(optimized, testset, args.metric),
                }
            result = update_status(
                args.run_dir, state="completed", phase="done", finished_at=timestamp(),
                elapsed_seconds=round(time.monotonic() - started, 3),
                optimized_validation=optimized_validation,
                validation_delta=round(optimized_validation["score"] - baseline_validation["score"], 6),
                holdout=holdout,
                holdout_verified=bool(testset),
                optimized_artifact="optimized.json",
            )
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        finally:
            logger.removeHandler(file_handler)
            file_handler.close()
    except Exception as exc:
        # Do not persist exception messages: some providers include credentials in errors.
        update_status(
            args.run_dir, state="failed", phase="error", finished_at=timestamp(),
            elapsed_seconds=round(time.monotonic() - started, 3), error_type=type(exc).__name__,
        )
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("preflight", help="Offline dependency and secret presence checks")
    watch = subs.add_parser("inspect", help="Offline run status and artifact inspection")
    watch.add_argument("--run-dir", type=Path, required=True)
    run = subs.add_parser("optimize", help="Run a GEPA experiment")
    run.add_argument("--train", type=Path, required=True)
    run.add_argument("--val", type=Path, required=True)
    run.add_argument("--test", type=Path)
    run.add_argument("--run-dir", type=Path, required=True)
    run.add_argument("--metric", choices=("exact", "contains"), default="exact")
    budget = run.add_mutually_exclusive_group()
    budget.add_argument("--auto", choices=("light", "medium", "heavy"), default="light")
    budget.add_argument("--max-metric-calls", type=int)
    run.add_argument("--num-threads", type=int, default=1)
    args = parser.parse_args()
    if args.command == "preflight":
        return preflight()
    if args.command == "inspect":
        return inspect(args.run_dir)
    try:
        return optimize(args)
    except Exception as exc:
        # stderr should not accidentally contain provider-returned secrets.
        print("GEPA run failed: " + type(exc).__name__ + ". See the run status for evidence.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
