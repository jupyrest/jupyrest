from typing import Protocol, List, Annotated
from importlib.resources import files, as_file
from urllib import response

import json
from ..notebook_execution.entity import (
    NotebookExecution,
    NotebookExecutionStatus,
)
from ..notebook_execution.commands import accept, begin_execution
from ..notebook_execution.queries import (
    get_execution,
    get_execution_artifact,
    ExecutionArtifactType,
)
from .models import (
    NotebookExecutionRequest,
    NotebookExecutionResponse,
    NotebookResponse,
    NotebookList,
    NotebookExecutionAsyncResponse,
)
from ..error import (
    BaseError,
    InvalidInputSchema,
    InternalError,
    InvalidExecutionState,
    NotebookExecutionNotFound,
    NotebookNotFound,
    NotebookExecutionArtifactNotFound,
    FileObjectNotFound,
)
from ..contracts import DependencyBag
from fastapi import FastAPI, Request, BackgroundTasks, HTTPException, status
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse


def create_asgi_app(deps: DependencyBag) -> FastAPI:

    jupyrest_api_app = FastAPI(title="Jupyrest API")

    @jupyrest_api_app.exception_handler(BaseError)
    def error_to_http_exception(request: Request, exc: BaseError):
        if isinstance(exc, (InvalidInputSchema, InvalidExecutionState)):
            status_code = 400
        elif isinstance(
            exc,
            (
                NotebookExecutionNotFound,
                NotebookNotFound,
                NotebookExecutionArtifactNotFound,
                FileObjectNotFound,
            ),
        ):
            status_code = 404
        else:
            status_code = 500
        return JSONResponse(status_code=status_code, content=exc.dict())

    @jupyrest_api_app.get("/api/notebooks", response_model=NotebookList)
    async def get_notebook_list():
        notebook_repo = deps.notebook_repository
        notebook_ids = []
        async for notebook_id in notebook_repo.iter_notebook_ids():  # type: ignore
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
        "/api/notebooks/{notebook_id}/execute",
        response_model=NotebookExecutionAsyncResponse,
        status_code=202,
    )
    async def post_notebook_execution(
        notebook_id: str,
        req: NotebookExecutionRequest,
        background_tasks: BackgroundTasks,
    ):
        execution = await accept(
            notebook_id=notebook_id, parameters=req.parameters, deps=deps
        )
        background_tasks.add_task(begin_execution, execution=execution, deps=deps)
        content = NotebookExecutionAsyncResponse(
            execution_id=execution.execution_id,
            status=execution.status,
            notebook_id=execution.notebook_id,
        )
        return content

    @jupyrest_api_app.get(
        "/api/notebook_executions/{execution_id}",
        response_model=NotebookExecutionResponse,
    )
    async def get_notebook_execution(execution_id: str):
        execution = await get_execution(execution_id=execution_id, deps=deps)

        notebook_execution_response = NotebookExecutionResponse(
            execution_id=execution.execution_id,
            status=execution.status,
            notebook_id=execution.notebook_id,
            parameters=execution.parameters,
            execution_accepted_ts=execution.accepted_time,
        )
        if execution.start_time:
            notebook_execution_response.execution_start_ts = execution.start_time
        if execution.completion_details:
            notebook_execution_response.execution_end_ts = (
                execution.completion_details.end_time
            )
            notebook_execution_response.execution_completion_status = (
                execution.completion_details.completion_status
            )
            artifacts = {}
            if execution.completion_details.output is not None:
                notebook_execution_response.has_output = True
                artifacts[ExecutionArtifactType.OUTPUT.value] = f"/api/notebook_executions/{execution_id}/artifacts/{ExecutionArtifactType.OUTPUT.value}"
            else:
                notebook_execution_response.has_output = False
            if execution.completion_details.exception is not None:
                notebook_execution_response.has_exception = True
                artifacts[ExecutionArtifactType.EXCEPTION.value] = f"/api/notebook_executions/{execution_id}/artifacts/{ExecutionArtifactType.EXCEPTION.value}"
            else:
                notebook_execution_response.has_exception = False
            if execution.completion_details.html is not None:
                artifacts[ExecutionArtifactType.HTML.value] = f"/api/notebook_executions/{execution_id}/artifacts/{ExecutionArtifactType.HTML.value}"
            if execution.completion_details.ipynb is not None:
                artifacts[ExecutionArtifactType.IPYNB.value] = f"/api/notebook_executions/{execution_id}/artifacts/{ExecutionArtifactType.IPYNB.value}"
            if execution.completion_details.html_report is not None:
                artifacts[ExecutionArtifactType.HTML_REPORT.value] = f"/api/notebook_executions/{execution_id}/artifacts/{ExecutionArtifactType.HTML_REPORT.value}"
            notebook_execution_response.artifacts = artifacts
        return notebook_execution_response

    @jupyrest_api_app.get(
        "/api/notebook_executions/{execution_id}/artifacts/{artifact_type}",
    )
    async def get_notebook_execution_artifact(
        execution_id: str, artifact_type: ExecutionArtifactType
    ):
        content = await get_execution_artifact(
            execution_id=execution_id, deps=deps, artifact_type=artifact_type
        )

        if artifact_type in (
            ExecutionArtifactType.HTML,
            ExecutionArtifactType.HTML_REPORT,
        ):
            return HTMLResponse(content=content)
        elif artifact_type in (
            ExecutionArtifactType.IPYNB,
            ExecutionArtifactType.OUTPUT,
        ):
            return JSONResponse(content=json.loads(content))
        elif artifact_type == ExecutionArtifactType.EXCEPTION:
            return PlainTextResponse(content=content)
        else:
            raise HTTPException(status_code=404, detail="Artifact not found")

    return jupyrest_api_app
