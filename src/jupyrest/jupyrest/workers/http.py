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
from pydantic import BaseModel, Json
from jupyrest.nbschema import NbSchemaEncoder
from jupyrest.errors import (
    BadInput,
    BaseError,
    InternalError,
    PluginNotFound,
    NotebookNotFound,
    InputSchemaValidationError,
)
from typing import Dict, Optional, Any, List, Union
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from uuid import uuid4
from nbconvert import HTMLExporter
from opentelemetry import trace
import azure.functions as func
from abc import ABC, abstractmethod
from pathlib import Path

tracer = trace.get_tracer(__name__)


class NotebookExecutionRequest(BaseModel):
    notebook: str
    parameters: Dict


class NotebookExecutionResponse(BaseModel):
    id: str
    status: str
    notebook: str
    parameters: Dict
    exception: Optional[str] = None
    output: Optional[Any] = None
    html: Optional[str] = None
    ipynb: Optional[str] = None


class NotebookResponse(BaseModel):
    notebook_id: str
    input_schema: Dict
    output_schema: Dict


class NotebookList(BaseModel):
    notebooks: List[str]


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


class BaseNotebookEventStoreRepository(ABC):
    async def save(self, id: str, notebook_event_store: NotebookEventStore):
        ...

    async def get(self, id: str) -> NotebookEventStore:
        ...

    async def exists(self, id: str) -> bool:
        ...


class InMemoryNotebookEventStoreRepository(BaseNotebookEventStoreRepository):
    def __init__(self) -> None:
        self._store: Dict[str, NotebookEventStore] = {}

    async def save(self, id: str, notebook_event_store: NotebookEventStore):
        self._store[id] = notebook_event_store

    async def get(self, id: str) -> NotebookEventStore:
        return self._store[id]

    async def exists(self, id: str) -> bool:
        return id in self._store


def create_dev_app(
    worker: Worker, event_store_repository: BaseNotebookEventStoreRepository
):

    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
    from pathlib import Path
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI(title="Jupyrest Web Server", debug=True)

    static_files = Path(__file__).parent / "static"
    # Mount the directory containing the HTML file as a static directory
    app.mount("/static", StaticFiles(directory=static_files), name="static")

    worker.plugin_man.register_entry_points()
    plugin_name = PluginManager.DEFAULT_PLUGIN_NAME
    plugin = worker.plugin_man.load(plugin_name=plugin_name)
    if plugin is None:
        raise Exception(f"Plugin with name {plugin_name} not found")

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
            return HTTPException(
                status_code=400,
                detail=f"Bad input: {error.details}",
            )
        elif isinstance(error, InternalError):
            return HTTPException(status_code=500, detail=error.details)
        else:
            return HTTPException(status_code=500)

    @app.get("/api/Notebooks", response_model=Union[NotebookList, NotebookResponse])
    async def get_notebook(id: Optional[str] = None):
        resolver = plugin.get_resolver()
        notebook_id = id
        if notebook_id:
            result = await worker.get_notebook_async(
                plugin_name=plugin_name, notebook_id=notebook_id
            )
            if isinstance(result, BaseError):
                raise to_http_exception(result)
            input_schema = plugin.get_input_schema(notebook_id=notebook_id)
            output_schema = plugin.get_output_schema(notebook_id=notebook_id)
            resp = NotebookResponse(
                notebook_id=notebook_id,
                input_schema=input_schema,
                output_schema=output_schema,
            )
            return resp
        else:
            notebook_ids = list(resolver.iter_notebook_ids())
            return NotebookList(notebooks=notebook_ids)

    @app.post(
        "/api/NotebookExecutions",
        response_model=NotebookExecutionResponse,
        response_model_exclude_unset=True,
    )
    async def post(req: NotebookExecutionRequest) -> NotebookExecutionResponse:
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
        event_store = NotebookEventStore(notebook=result)
        await event_store_repository.save(
            id=execution_id, notebook_event_store=event_store
        )

        notebook_executed = event_store.get_event(NotebookExecuted)
        assert isinstance(notebook_executed, NotebookExecuted)
        status = "COMPLETED" if notebook_executed.exception is None else "FAILED"
        response = NotebookExecutionResponse(
            id=execution_id,
            status=status,
            notebook=req.notebook,
            parameters=req.parameters,
        )
        return response

    @app.get(
        "/api/NotebookExecutions",
        response_model=NotebookExecutionResponse,
        response_model_exclude_unset=True,
    )
    async def get(
        executionId: str,
        html: bool = False,
        report: bool = False,
        output: bool = False,
        ipynb: bool = False,
        view_html: bool = False,
    ):

        if not await event_store_repository.exists(id=executionId):
            raise HTTPException(
                status_code=404, detail=f"Execution {executionId} not found."
            )
        event_store = await event_store_repository.get(id=executionId)
        notebook = event_store.notebook
        execution_created = event_store.get_event(NotebookExecutionCreated)
        notebook_executed = event_store.get_event(NotebookExecuted)
        assert isinstance(notebook_executed, NotebookExecuted)
        assert isinstance(execution_created, NotebookExecutionCreated)
        status = "COMPLETED" if notebook_executed.exception is None else "FAILED"
        response = NotebookExecutionResponse(
            id=executionId,
            status=status,
            notebook=execution_created.notebook_id,
            parameters=execution_created.parameters,
            exception=notebook_executed.exception,
        )
        if view_html:
            return HTMLResponse(notebook_to_html(notebook=notebook, report_mode=report))
        if html:
            response.html = notebook_to_html(notebook=notebook, report_mode=report)
        if output:
            if notebook_executed.output_json_str is None:
                response.output = None
            else:
                response.output = json.loads(notebook_executed.output_json_str)
        if ipynb:
            response.ipynb = json.loads(notebook_to_str(notebook=notebook))
        return response

    return app


def create_azure_function(fastapi_app: FastAPI):
    app = func.Blueprint()

    # @app.function_name("JupyrestAzureFunction")
    # @app.route()
    # async def azure_function_main(req: func.HttpRequest, context: func.Context):
    #     nonlocal app
    #     nonlocal fastapi_app
    #     return await func.AsgiMiddleware(app=fastapi_app).handle_async(req=req, context=context)

    return app
