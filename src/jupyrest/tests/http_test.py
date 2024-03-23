import aiohttp
import pytest
from jupyrest.client2 import NotebookExecutionClient


@pytest.mark.anyio
async def test_execute_notebook(http_server: aiohttp.ClientSession):
    async with http_server as session:
        notebook_id = "error"
        parameters = {}
        client = NotebookExecutionClient(session)
        result = await client.execute_notebook_until_complete(notebook_id, parameters)
        print("Execution Result:", result)
        assert result is not None
        assert result["status"] == "COMPLETED"
        assert result["execution_completion_status"] == "FAILED"
