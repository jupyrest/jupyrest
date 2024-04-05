import aiohttp
import asyncio
from typing import Dict
from jupyrest.http.models import NotebookExecutionResponse, NotebookExecutionStatus, NotebookExecutionAsyncResponse


class JupyrestClient:
    def __init__(self, endpoint: str) -> None:
        self.endpoint = endpoint

    def session(self):
        return aiohttp.ClientSession(base_url=self.endpoint, raise_for_status=True)

    async def execute_notebook(self, notebook_id, parameters) -> NotebookExecutionAsyncResponse:
        async with self.session() as session:
            execute_url = f"/api/notebooks/{notebook_id}/execute"
            async with session.post(
                execute_url,
                json=dict(parameters=parameters),
            ) as response:
                response_json = await response.json()
                return NotebookExecutionAsyncResponse.parse_obj(response_json)

    async def poll(self, execution_id: str) -> NotebookExecutionResponse:
        execution_url = f"/api/notebook_executions/{execution_id}" 
        while True:
            async with self.session() as session:
                async with session.get(execution_url) as response:
                    response_json = await response.json()
                    execution_response = NotebookExecutionResponse.parse_obj(response_json)
                    if execution_response.status == NotebookExecutionStatus.COMPLETED:
                        return execution_response
                    else:
                        await asyncio.sleep(1)

    async def execute_notebook_until_complete(self, notebook_id, parameters):
        execution = await self.execute_notebook(notebook_id, parameters)
        return await self.poll(execution_id=execution.execution_id)
    
    
    async def get_execution(self, execution_id: str) -> NotebookExecutionResponse:
        async with self.session() as session:
            execution_url = f"/api/notebook_executions/{execution_id}"
            async with session.get(execution_url) as response:
                response_json = await response.json()
                return NotebookExecutionResponse.parse_obj(response_json)

    async def get_execution_html(self, execution_id: str, report_mode: bool = False) -> str:
        execution = await self.get_execution(execution_id)
        assert execution.artifacts is not None
        async with self.session() as session:
            url = execution.artifacts["html_report"] if report_mode else execution.artifacts["html"]
            async with session.get(url) as response:
                return await response.text()
            
    async def get_execution_ipynb(self, execution_id: str) -> Dict:
        execution = await self.get_execution(execution_id)
        assert execution.artifacts is not None
        async with self.session() as session:
            async with session.get(execution.artifacts["ipynb"]) as response:
                return await response.json()
    
    async def get_execution_output(self, execution_id: str):
        execution = await self.get_execution(execution_id)
        assert execution.artifacts is not None
        async with self.session() as session:
            async with session.get(execution.artifacts["output"]) as response:
                return await response.json()

    async def get_notebook(self, notebook_id: str):
        async with self.session() as session:
            async with session.get(f"/api/notebooks/{notebook_id}") as response:
                return await response.json()