from symbol import parameters
import aiohttp
import asyncio
from urllib.parse import urljoin


class NotebookExecutionClient:
    def __init__(self, session: aiohttp.ClientSession) -> None:
        self.session = session

    async def execute_notebook(self, notebook_id, parameters):
        execute_url = f"/api/notebooks/{notebook_id}/execute"
        async with self.session.post(
            execute_url, json=dict(parameters=parameters)
        ) as response:
            if response.status == 202:
                location_url = response.headers.get("Location")
                return location_url

    async def poll_location(self, location_url):
        found = False
        while True:
            async with self.session.get(
                location_url, allow_redirects=False
            ) as response:
                if response.status == 302:
                    location_url = str(response.headers.get("Location"))
                    found = True
                    continue
                elif response.status == 200:
                    if not found:
                        retry_after = int(response.headers.get("Retry-After", "0"))
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        return await response.json()
                else:
                    # Handle other status codes appropriately
                    response.raise_for_status()

    async def execute_notebook_until_complete(self, notebook_id, parameters):
        location_url = await self.execute_notebook(notebook_id, parameters)
        if location_url:
            return await self.poll_location(location_url)


# async def main():
#     async with aiohttp.ClientSession() as session:
#         notebook_id = "error"
#         parameters = {}
#         base_url = "http://localhost:5050/"
#         location_url = await execute_notebook(base_url, session, notebook_id, parameters)
#         if location_url:
#             result = await poll_location(base_url, session, location_url)
#             print("Execution Result:", result)
