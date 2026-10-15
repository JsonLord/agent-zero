import asyncio
import logging

from agent import AgentContext, AgentContextType, LoopData
from helpers.extension import Extension
from helpers.notification import (
    NotificationManager,
    NotificationPriority,
    NotificationType,
)
from plugins._chat_naming.helpers import naming

log = logging.getLogger(__name__)
# AgentContext uses a persistent shared event loop; retain one task per context.
TASKS: dict[str, asyncio.Task] = {}


def _finished(context_id, task):
    if TASKS.get(context_id) is task:
        TASKS.pop(context_id, None)
    if not task.cancelled():
        error = task.exception()
        if error:
            log.warning("Chat naming worker failed: %s", type(error).__name__)


class RenameChat(Extension):
    async def execute(self, loop_data: LoopData | None = None, **kwargs):
        if not self.agent or self.agent is not self.agent.context.agent0:
            return
        if self.agent.context.type != AgentContextType.USER:
            return

        config = naming.get_config(self.agent)
        if not config["automatic_naming"]:
            return

        mode = config["automatic_naming_mode"]
        if mode == naming.MODE_ONCE and str(self.agent.context.name or "").strip():
            return

        messages = naming.get_user_messages(
            self.agent,
            limit=None if mode == naming.MODE_ONCE else naming.RECENT_USER_MESSAGES,
        )
        if not messages:
            return
        if mode == naming.MODE_ONCE:
            messages = messages[:1]

        context_id = self.agent.context.id
        pending = TASKS.get(context_id)
        if pending and not pending.done():
            if mode == naming.MODE_ONCE or getattr(
                pending, "naming_sequence", None
            ) == naming.latest_user_sequence(self.agent):
                return
            pending.cancel()
        task = asyncio.create_task(
            self.change_name(
                messages=messages,
                snapshot=(
                    self.agent.context.name,
                    getattr(self.agent.context, "_chat_naming_revision", 0),
                ),
                request_sequence=naming.latest_user_sequence(self.agent),
                only_if_unnamed=(mode == naming.MODE_ONCE),
            )
        )
        task.naming_sequence = naming.latest_user_sequence(self.agent)
        TASKS[context_id] = task
        task.add_done_callback(lambda done: _finished(context_id, done))

    async def change_name(
        self,
        *,
        messages: list[str],
        request_sequence: int,
        only_if_unnamed: bool,
        snapshot: tuple | None = None,
    ) -> None:
        if not self.agent:
            return

        context = self.agent.context
        initial_name, revision = snapshot or (
            context.name,
            getattr(context, "_chat_naming_revision", 0),
        )
        try:
            new_name = await naming.generate_name(
                self.agent,
                user_messages=messages,
                current_name=self.agent.context.name,
            )
            with naming.NAME_LOCK, AgentContext._contexts_lock:
                if only_if_unnamed and str(self.agent.context.name or "").strip():
                    log.info("Chat naming result discarded: existing title")
                    return
                if (
                    not only_if_unnamed
                    and naming.latest_user_sequence(self.agent) != request_sequence
                ):
                    log.info("Chat naming result discarded: stale sequence")
                    return
                if AgentContext.get(self.agent.context.id) is not self.agent.context:
                    log.info("Chat naming result discarded: expired context")
                    return
                if (
                    context.name != initial_name
                    or getattr(context, "_chat_naming_revision", 0) != revision
                ):
                    log.info("Chat naming result discarded: manual or newer title")
                    return
                if not naming.get_config(self.agent)["automatic_naming"]:
                    log.info("Chat naming result discarded: naming disabled")
                    return
                naming.save_context_name(self.agent, new_name)

        except asyncio.CancelledError:
            log.info("Chat naming cancelled")
            raise
        except Exception as error:  # noqa: BLE001 - naming must never fail the main task
            status = getattr(error, "status_code", None)
            reason = (
                "timeout"
                if isinstance(error, TimeoutError)
                else "auth_failure"
                if status in (401, 403)
                else "invalid_response"
                if isinstance(error, ValueError)
                else "provider_error"
            )
            log.warning(
                "Automatic chat naming failed: %s (%s)", reason, type(error).__name__
            )
            NotificationManager.send_notification(
                type=NotificationType.ERROR,
                priority=NotificationPriority.NORMAL,
                title="Chat Naming Failed",
                message="Automatic chat naming failed. The existing title was preserved; you can retry manually.",
                detail=(
                    "Automatic chat naming uses the Utility Model. Check Settings > Models > "
                    "Utility Model, provider/API key, and network reachability."
                ),
                display_time=10,
                group="chat_naming",
                id=f"chat_naming_failed_{self.agent.context.id}",
            )
