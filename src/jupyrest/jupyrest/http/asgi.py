from typing import Protocol, List, Annotated
from importlib.resources import files, as_file
from ..notebook_execution.entity import (
    NotebookExecution,
    NotebookExecutionStatus,
)
from ..notebook_execution.commands import create, accept, begin_execution
from .models import (
    NotebookExecutionRequest,
    NotebookExecutionResponse,
    NotebookResponse,
    NotebookList,
    NotebookExecutionAsyncResponse,
)
from ..errors2 import (
    BaseError,
    InvalidInputSchema,
    InternalError,
    InvalidExecutionState,
    NotebookExecutionNotFound,
    NotebookNotFound,
)
from .. import project_root
import json
from ..dependencies import DependencyBag, NotebookRepository
from fastapi import FastAPI, Request, BackgroundTasks, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

def create_asgi_app(deps: DependencyBag) -> FastAPI:

    jupyrest_api_app = FastAPI(title="Jupyrest API")

    jupyrest_api_app.mount(
        "/static",
        StaticFiles(directory=str(project_root / "workers" / "static")),
        name="static",
    )

    @jupyrest_api_app.exception_handler(BaseError)
    def error_to_http_exception(request: Request, exc: BaseError):
        if isinstance(exc, (InvalidInputSchema, InvalidExecutionState)):
            status_code = 400
        elif isinstance(exc, (NotebookExecutionNotFound, NotebookNotFound)):
            status_code = 404
        else:
            status_code = 500
        return JSONResponse(status_code=status_code, content=exc.dict())

    @jupyrest_api_app.get("/api/notebooks", response_model=NotebookList)
    async def get_notebook_list():
        notebook_repo = deps.notebook_repository
        notebook_ids = []
        async for notebook_id in (await notebook_repo.iter_notebook_ids()):
            notebook_ids.append(notebook_id)
        return NotebookList(notebooks=notebook_ids)

    @jupyrest_api_app.get(
        "/api/notebooks/{notebook_id}", response_model=NotebookResponse
    )
    async def get_notebook(notebook_id: str):
        notebook = await deps.notebook_repository.get(notebook_id=notebook_id)
        input_schema = notebook.resolved_input_schema or {}
        output_schema = notebook.resolved_output_schema or {}
        return NotebookResponse(
            notebook_id=notebook_id,
            input_schema=input_schema,
            output_schema=output_schema,
        )

    @jupyrest_api_app.post(
        "/api/notebooks/{notebook_id}/execute", response_model=NotebookExecutionAsyncResponse
    )
    async def post_notebook_execution(
        notebook_id: str,
        req: NotebookExecutionRequest,
        background_tasks: BackgroundTasks):
        execution = create(
            notebook_id=notebook_id, parameters=req.parameters
        )
        await accept(execution=execution, deps=deps)
        background_tasks.add_task(
            begin_execution,
            execution=execution,
            deps=deps)
        content = NotebookExecutionAsyncResponse(
            id=execution.execution_id,
            status=execution.status,
            notebook_id=execution.notebook_id,
        )
        headers = {
            "Location": f"/api/notebook_executions/{execution.execution_id}",
        }
        return JSONResponse(
            status_code=202,
            content=content.dict(),
            headers=headers
        )


    @jupyrest_api_app.get(
        "/api/notebook_executions/{execution_id}",
        response_model=NotebookExecutionResponse,
    )
    async def get_notebook_execution(execution_id: str):
        execution_repository = deps.notebook_execution_repository
        execution = await execution_repository.get(
            execution_id=execution_id
        )
        notebook_execution_response = NotebookExecutionResponse(
            execution_id=execution.execution_id,
            status=execution.status,
            notebook_id=execution.notebook_id,
            parameters=execution.parameters,
        )
        return notebook_execution_response


    @jupyrest_api_app.get(
        "/api/notebook_executions/{execution_id}",
        response_model=NotebookExecutionResponse,
    )
    async def get_notebook_execution_artifact(execution_id: str):
        pass


    return jupyrest_api_app
