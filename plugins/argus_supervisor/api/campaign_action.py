from helpers.api import ApiHandler, Request, Response
from plugins.argus_supervisor.helpers import service
from plugins.argus_supervisor.helpers.models import SupervisorError


class CampaignAction(ApiHandler):
    async def process(self, input: dict, request: Request):
        try:
            return {
                "campaign": await service.action(
                    input.get("campaign_id"), input.get("action"), input
                )
            }
        except SupervisorError as error:
            return Response(status=409, response=str(error))
