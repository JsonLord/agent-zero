import aiohttp
import asyncio
from python.helpers import runtime

# List of public SearxNG instances
# Find more at https://searx.space/
INSTANCES = [
    "https://searx.be/search",
    "https://searx.info/search",
    "https://searx.work/search",
    "https://searx.priv.au/search",
    "https://searx.tiekoetter.com/search",
    "https://searx.baczek.me/search",
    "https://searx.rodeo/search",
]

async def search(query:str):
    return await _search(query=query)

async def _search(query:str):
    timeout = aiohttp.ClientTimeout(total=30)
    for instance in INSTANCES:
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(instance, data={"q": query, "format": "json"}) as response:
                    if response.status == 200:
                        try:
                            return await response.json()
                        except aiohttp.client_exceptions.ContentTypeError:
                            # This instance is not returning JSON, so we try the next one
                            continue
        except (aiohttp.ClientConnectorError, asyncio.TimeoutError):
            # This instance is not reachable or timed out, so we try the next one
            continue
    # If all instances fail, we return an error
    raise Exception("All SearxNG instances failed to respond.")
