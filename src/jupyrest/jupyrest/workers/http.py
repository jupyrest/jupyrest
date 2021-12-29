from jupyrest.domain import (
    NotebookEventStore,
    NotebookExecuted,
    NotebookExecutionCreated,
)
from nbformat import NotebookNode
import nbformat
import json
from starlette.responses import HTMLResponse
from jupyrest.plugin import PluginManager
from jupyrest.workers.base import Worker
from pydantic import BaseModel
from jupyrest.nbschema import NbSchemaEncoder
from jupyrest.errors import (
    BadInput,
    BaseError,
    InternalError,
    PluginNotFound,
    NotebookNotFound,
    InputSchemaValidationError,
)
from typing import Dict
from fastapi import FastAPI, HTTPException
from uuid import uuid4
from nbconvert import HTMLExporter
from opentelemetry import trace

tracer = trace.get_tracer(__name__)


class NotebookRequest(BaseModel):
    notebook: str
    parameters: Dict


class NotebookResponse(BaseModel):
    id: str
    status: str
    notebook: str
    parameters: Dict


def notebook_to_html(notebook: NotebookNode, report_mode=False) -> str:
    with tracer.start_as_current_span("notebook_to_html"):
        exporter = HTMLExporter()
        if report_mode:
            exporter = HTMLExporter(exclude_output_prompt=True, exclude_input=True)
        (body, _) = exporter.from_notebook_node(notebook)
        return body


def notebook_to_str(notebook: NotebookNode) -> str:
    with tracer.start_as_current_span("notebook_to_str"):
        return nbformat.writes(
            notebook, version=nbformat.NO_CONVERT, cls=NbSchemaEncoder
        )


def create_dev_app(worker: Worker):
    app = FastAPI(title="Jupyrest Web Server", debug=True)
    notebooks: Dict[str, NotebookNode] = {}

    plugin_name = PluginManager.DEFAULT_PLUGIN_NAME

    def to_http_exception(error: BaseError) -> HTTPException:
        if isinstance(error, PluginNotFound):
            return HTTPException(
                status_code=404, detail=f"Plugin {error.plugin_name} not found."
            )
        elif isinstance(error, NotebookNotFound):
            return HTTPException(
                status_code=404, detail=f"Notebook {error.notebook_id} not found."
            )
        elif isinstance(error, InputSchemaValidationError):
            return HTTPException(
                status_code=400,
                detail=f"Input schema validation error: {error.validation.error}",
            )
        elif isinstance(error, BadInput):
            return HTTPException(status_code=400, detail=f"Bad input: {error.details}",)
        elif isinstance(error, InternalError):
            return HTTPException(status_code=500, detail=error.details)
        else:
            return HTTPException(status_code=500)

    @app.post("/api/NotebookExecutions")
    async def post(req: NotebookRequest) -> NotebookResponse:
        # create NotebookExecutionRequest
        notebook_id = req.notebook
        parameters = req.parameters
        execution_id = str(uuid4())
        # execute notebook
        result = await worker.execute_notebook_async(
            plugin_name=plugin_name,
            notebook_id=notebook_id,
            parameters=parameters,
            parameterize_only=False,
        )

        if isinstance(result, BaseError):
            raise to_http_exception(result)

        # save execution
        notebooks[execution_id] = result

        event_store = NotebookEventStore(notebook=result)
        notebook_executed = event_store.get_event(NotebookExecuted)
        assert isinstance(notebook_executed, NotebookExecuted)
        status = "COMPLETED" if notebook_executed.exception is None else "FAILED"
        response = NotebookResponse(
            id=execution_id,
            status=status,
            notebook=req.notebook,
            parameters=req.parameters,
        )
        return response

    @app.get("/api/NotebookExecutions")
    async def get(
        executionId: str,
        html: bool = False,
        report: bool = False,
        output: bool = False,
        ipynb: bool = False,
        view_html: bool = False,
    ):

        if executionId not in notebooks:
            raise HTTPException(
                status_code=404, detail=f"Execution {executionId} not found."
            )
        notebook = notebooks[executionId]
        event_store = NotebookEventStore(notebook=notebook)
        execution_created = event_store.get_event(NotebookExecutionCreated)
        notebook_executed = event_store.get_event(NotebookExecuted)
        assert isinstance(notebook_executed, NotebookExecuted)
        assert isinstance(execution_created, NotebookExecutionCreated)
        status = "COMPLETED" if notebook_executed.exception is None else "FAILED"
        response = NotebookResponse(
            id=executionId,
            status=status,
            notebook=execution_created.notebook_id,
            parameters=execution_created.parameters,
        ).dict()
        response["exception"] = notebook_executed.exception
        if view_html:
            return HTMLResponse(notebook_to_html(notebook=notebook, report_mode=report))
        if html:
            response["html"] = notebook_to_html(notebook=notebook, report_mode=report)
        if output:
            if notebook_executed.output_json_str is None:
                response["output"] = None
            else:
                response["output"] = json.loads(notebook_executed.output_json_str)
        if ipynb:
            response["ipynb"] = notebook_to_str(notebook=notebook)
        return response

    return app
