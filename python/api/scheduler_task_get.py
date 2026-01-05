from python.helpers.api import ApiHandler, Input, Output, Request
from python.helpers.task_scheduler import TaskScheduler
import traceback
from python.helpers.print_style import PrintStyle
from python.helpers.localization import Localization


class SchedulerTaskGet(ApiHandler):
    async def process(self, input: Input, request: Request) -> Output:
        """
        Get a single task from the scheduler by UUID
        """
        try:
            # Get timezone from input (do not set if not provided, we then rely on poll() to set it)
            if timezone := input.get("timezone", None):
                Localization.get().set_timezone(timezone)

            # Get task scheduler
            scheduler = TaskScheduler.get()
            await scheduler.reload()

            task_uuid = input.get("uuid")
            if not task_uuid:
                raise ValueError("Missing required field: uuid")

            # Use the scheduler's convenience method for task serialization
            task = scheduler.serialize_task(task_uuid)

            if not task:
                return {"error": f"Task not found: {task_uuid}"}

            return {"task": task}

        except Exception as e:
            PrintStyle.error(f"Failed to get task: {str(e)} {traceback.format_exc()}")
            return {"error": f"Failed to get task: {str(e)} {traceback.format_exc()}"}
