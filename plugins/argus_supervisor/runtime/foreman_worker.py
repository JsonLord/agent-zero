"""Real Foreman responsibility/policy evaluation, with no execution adapter."""

import asyncio
import json
import sys


async def assess(request):
    from foreman.config import FactoryConfig
    from foreman.foreman.jev import JevForemanModel
    from foreman.models import FactoryState, WorkerRecord, WorkerStatus, WorkerType
    from foreman.observation import FactoryObservation
    from foreman.policy import FactoryPolicy
    from foreman.responsibilities import builtin_registry

    config = FactoryConfig()
    registry = builtin_registry(config).routed(
        [
            "core.completion",
            "core.verification",
            "core.worker-health",
            "core.human-escalation",
        ]
    )
    if request.get("operation") == "verify":
        return {"responsibilities": [r.id for r in registry.responsibilities]}
    running = request["state"] in {"working", "submitted", "running"}
    worker = WorkerRecord(
        worker_id="remote-worker",
        worker_type=WorkerType.CODING,
        mission=request["objective"],
        status=WorkerStatus.RUNNING if running else WorkerStatus.COMPLETED,
    )
    observation = FactoryObservation(
        original_job=request["objective"],
        current_operation={"trust": "UNTRUSTED_REMOTE_DATA"},
        run_id=request["run_id"],
        factory_status=request["state"],
        iteration=1,
        active_workers=[worker.model_dump(mode="json")] if running else [],
        worker_history=[],
        latest_worker_output=json.dumps(request["evidence"]),
        worker_exit_status={},
        worker_elapsed_seconds={},
        git_status="not observed",
        git_diff="not observed",
        changed_files=[],
        test_results=[],
        verification_results=[],
        recent_events=[],
        previous_result=None,
        previous_intervention=None,
        attempts=1,
        failures=[],
        elapsed_factory_seconds=0,
    )
    model = JevForemanModel(timeout_seconds=10)
    try:
        result = await model.assess(observation, registry.checks())
        state = FactoryState(
            run_id=request["run_id"],
            job=request["objective"],
            repository="remote:unobserved",
            iteration=1,
            workers=[worker],
            active_workers=[worker.worker_id] if running else [],
        )
        decision = FactoryPolicy(
            config, registry, enforce_iteration_limit=False
        ).decide(state, result)
        return {
            "directive": "STEER_WORKER"
            if decision.action.value == "START_WORKER"
            else decision.action.value
        }
    finally:
        await model.close()


if __name__ == "__main__":
    try:
        result = asyncio.run(assess(json.loads(sys.stdin.buffer.read(32769))))
    except Exception:  # noqa: BLE001 - isolated process boundary returns only a safe code
        result = {"error": "foreman_assessment_unavailable"}
    sys.stdout.write(json.dumps(result))
