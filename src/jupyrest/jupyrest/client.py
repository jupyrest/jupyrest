import aiohttp
import asyncio
import time

class NotebookExecutionClient:
    def __init__(self, base_url):
        self.base_url = base_url

    async def execute_notebook(self, notebook_id):
        execute_url = f"{self.base_url}/notebooks/{notebook_id}/execute"
        async with aiohttp.ClientSession() as session:
            async with session.post(execute_url) as response:
                if response.status != 202:
                    raise RuntimeError(f"Failed to execute notebook. Status code: {response.status}")
                location_header = response.headers.get("Location")
                if not location_header:
                    raise RuntimeError("Location header not found")
                data = await response.json()
                execution_id = data.get("id")
                return execution_id

    async def check_execution_status(self, execution_id):
        execution_url = f"{self.base_url}/notebook_executions/{execution_id}"
        while True:
            async with aiohttp.ClientSession() as session:
                async with session.get(execution_url) as response:
                    data = await response.json()
                    status = data.get("status")
                    if status == "completed":
                        return data
                    elif status == "failed":
                        raise RuntimeError("Notebook execution failed")
                    await asyncio.sleep(1)

# Example usage:
async def main():
    client = NotebookExecutionClient("http://example.com/api")
    execution_id = await client.execute_notebook("test_notebook")
    execution_data = await client.check_execution_status(execution_id)
    print("Execution data:", execution_data)

asyncio.run(main())
