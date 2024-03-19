from symbol import parameters
import aiohttp
import asyncio
from urllib.parse import urljoin

async def execute_notebook(base_url, session, notebook_id, parameters):
    execute_url = urljoin(base_url, f"/api/notebooks/{notebook_id}/execute")
    async with session.post(execute_url, json=dict(parameters=parameters)) as response:
        if response.status == 202:
            location_url = response.headers.get('Location')
            return location_url

async def poll_location(base_url, session, location_url):
    location_url = urljoin(base_url, location_url)
    found = False
    while True:
        async with session.get(location_url, allow_redirects=False) as response:
            if response.status == 302:
                location_url = urljoin(base_url, response.headers.get('Location'))
                found = True
                continue
            elif response.status == 200:
                if not found:
                    retry_after = int(response.headers.get('Retry-After', '0'))
                    await asyncio.sleep(retry_after)
                    continue
                else:
                    return await response.json()
            else:
                # Handle other status codes appropriately
                response.raise_for_status()

async def main():
    async with aiohttp.ClientSession() as session:
        notebook_id = "error"
        parameters = {}
        base_url = "http://localhost:5050/"
        location_url = await execute_notebook(base_url, session, notebook_id, parameters)
        if location_url:
            result = await poll_location(base_url, session, location_url)
            print("Execution Result:", result)

if __name__ == "__main__":
    asyncio.run(main())
