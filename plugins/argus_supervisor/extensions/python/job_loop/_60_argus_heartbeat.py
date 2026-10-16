from helpers.extension import Extension
from plugins.argus_supervisor.helpers import service


class ArgusHeartbeat(Extension):
    async def execute(self, **kwargs):
        # Do not hold the scheduler while a significant event invokes a model.
        service.kick()
