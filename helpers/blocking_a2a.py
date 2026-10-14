import asyncio
import os
import time
from fasta2a.task_manager import TaskManager
from fasta2a.schema import SendMessageResponse, SendMessageResult


class BlockingTaskManager(TaskManager):
    async def send_message(self, request):
        response = await super().send_message(request)
        config = request["params"].get("configuration") or {}
        if not config.get("blocking", False):
            return response
        task_id = response["result"]["task"]["id"]
        timeout = min(
            max(float(os.getenv("A2A_BLOCKING_TIMEOUT", "60")), 1),
            90,
        )
        deadline = time.monotonic() + timeout
        terminal_states = {
            "completed",
            "failed",
            "canceled",
            "rejected",
            "input-required",
            "auth-required",
        }
        while True:
            task = await self.storage.load_task(task_id)
            if task and task["status"]["state"] in terminal_states:
                return SendMessageResponse(
                    jsonrpc="2.0",
                    id=request["id"],
                    result=SendMessageResult(task=task),
                )
            if time.monotonic() >= deadline:
                return SendMessageResponse(
                    jsonrpc="2.0",
                    id=request["id"],
                    result=SendMessageResult(
                        task=task or response["result"]["task"]
                    ),
                )
            await asyncio.sleep(0.5)
