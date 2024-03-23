from hmac import new
import aiohttp
import asyncio
from urllib.parse import urljoin
import logging
from jupyrest.http.models import NotebookExecutionResponse


log = logging.getLogger(__name__)
class NotebookExecutionClient:

    def __init__(self, base_url):
        self.session = aiohttp.ClientSession(base_url=base_url)

    async def __aenter__(self):
        log.info("Opening session")
        await self.session.__aenter__()
        return self
    
    async def __aexit__(self, exc_type, exc, tb):
        log.info("Closing session")
        await self.session.close()

    def post_request(self, *args, **kwargs):
        return self.session.post(*args, **kwargs)

    def get_request(self, *args, **kwargs):
        return self.session.get(*args, **kwargs)

    async def execute_notebook(self, notebook_id: str, parameters) -> str:
        execute_url = f"/api/notebooks/{notebook_id}/execute"
        async with self.post_request(execute_url, json={"parameters": parameters}, raise_for_status=True) as response:
            if response.status == 202:
                location_url = response.headers.get('Location')
                if location_url is not None:
                    log.info(f"Execution started at {location_url}")
                    return location_url
                else:
                    raise Exception(f"Location header not found in response")
            else:
                response.raise_for_status()
                raise Exception(f"Failed to start execution, expected 202 received {response.status}")

    async def poll_location(self, location_url: str) -> NotebookExecutionResponse:
        found = False
        while True:
            async with self.get_request(location_url, allow_redirects=False, raise_for_status=True) as response:
                if response.status == 302:
                    new_location = response.headers.get('Location')
                    if new_location is None:
                        raise Exception(f"Location header not found in 302 response")
                    found = True
                    location_url = new_location
                    continue
                elif response.status == 200:
                    if not found:
                        retry_after = int(response.headers.get('Retry-After', '0'))
                        await asyncio.sleep(retry_after)
                        continue
                    else:
                        return NotebookExecutionResponse.parse_obj(await response.json())
                else:
                    response.raise_for_status()
    
    async def execute_and_poll(self, notebook_id: str, parameters):
        location_url = await self.execute_notebook(notebook_id, parameters)
        return await self.poll_location(location_url)

async def main():
    async with aiohttp.ClientSession() as session:
        notebook_id = "error"
        parameters = {}
        base_url = "http://localhost:5050/"
        async with NotebookExecutionClient(base_url) as client:
            result = await client.execute_and_poll(notebook_id, parameters)
        print(result)
if __name__ == "__main__":
    asyncio.run(main())
