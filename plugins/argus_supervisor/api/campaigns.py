from helpers.api import ApiHandler, Request, Response
from plugins.argus_supervisor.helpers import service
from plugins.argus_supervisor.helpers.models import SupervisorError


class Campaigns(ApiHandler):
    async def process(self, input: dict, request: Request):
        try:
            if input.get("action") == "create":
                return {"campaign": service.create(input)}
            store = service.get().store
            if input.get("campaign_id"):
                return {"campaign": service.public(store.load(input["campaign_id"]))}
            return {"campaigns": [service.public(store.load(i)) for i in store.ids()]}
        except SupervisorError as error:
            return Response(status=409, response=str(error))
