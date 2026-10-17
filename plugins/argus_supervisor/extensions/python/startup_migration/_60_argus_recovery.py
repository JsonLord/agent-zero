from helpers.extension import Extension
from plugins.argus_supervisor.helpers import service


class ArgusRecovery(Extension):
    def execute(self, **kwargs):
        # startup_migration is synchronous. Retain bounded recovery through the
        # existing DeferredTask owner; never return an unawaited coroutine.
        service.kick(force=True)
