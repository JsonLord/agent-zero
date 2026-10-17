from helpers.api import ApiHandler, Request, Response
from plugins.argus_supervisor.helpers import service
from plugins.argus_supervisor.helpers.models import SupervisorError


class Status(ApiHandler):
    async def process(self, input: dict, request: Request):
        try:
            supervisor = service.get()
            return {
                "enabled": True,
                "last_tick": supervisor.last_tick,
                "last_error": supervisor.last_error,
                "capabilities": supervisor.capabilities,
                "campaigns": [
                    service.public(supervisor.store.load(i))
                    for i in supervisor.store.ids()
                ],
            }
        except SupervisorError as error:
            return Response(status=409, response=str(error))
