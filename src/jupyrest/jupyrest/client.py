import aiohttp
import asyncio
import time
import json
from urllib.parse import urljoin

class NotebookExecutionClient:
    def __init__(self, base_url):
        self.base_url = base_url

    async def execute_notebook(self, notebook_id, parameters, max_seconds_timeout=300):
        execute_url = urljoin(self.base_url, f"/notebooks/{notebook_id}/execute")
        async with aiohttp.ClientSession() as session:
            async with session.post(execute_url, json=dict(parameters=parameters)) as response:
                response.raise_for_status()
                assert response.status == 202
                location_url = response.headers.get("Location")
                assert location_url is not None, "Location header not found"
                data = await response.json()
                execution_id = data.get("execution_id")
                assert execution_id is not None, "Execution id not found"
        num_retries = 0
        while True and num_retries < max_seconds_timeout:
            async with aiohttp.ClientSession() as session:
                async with session.get(urljoin(self.base_url, location_url), allow_redirects=True) as response:
                    num_retries += 1
                    response.raise_for_status()
                    if response.status == 200:
                        await asyncio.sleep(1)
                    elif response.status == 200:
                        data = await response.json()
                        return data

if __name__ == "__main__":
    # Example usage:
    async def main():
        client = NotebookExecutionClient("http://localhost:5050/api")
        l = set()
        for x in range(1):
            t = client.execute_notebook("error", parameters={})
            l.add(t)
        await asyncio.gather(*l)
        # execution_data = await client.check_execution_status(execution_id)
        # print("Execution data:", execution_data)

    asyncio.run(main())
