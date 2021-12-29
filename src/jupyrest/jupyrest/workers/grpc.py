from json.decoder import JSONDecodeError

import logging
from uuid import uuid4
from typing import cast, Dict, Tuple
import pydantic
from typing import Optional, Any, Union
from nbformat.notebooknode import NotebookNode
from jupyrest.workers.base import Worker
from jupyrest.workers.generated import jupyrest_pb2 as grpc_models
from jupyrest.workers.generated import jupyrest_pb2_grpc as grpc_service
from jupyrest import errors
from jupyrest.nbschema import NbSchemaEncoder
from opentelemetry import trace
from opentelemetry.context import Context
from opentelemetry.trace.propagation.tracecontext import TraceContextTextMapPropagator
from grpc.aio import ServicerContext, Channel, Metadata
import json
import nbformat

logger = logging.getLogger(__name__)
tracer = trace.get_tracer(__name__)


class GrpcUtils:

    SPAN_METADATA_KEY = "otelspan"

    @classmethod
    def inject_span_context(cls, metadata: Metadata):
        span_context = {}
        TraceContextTextMapPropagator().inject(carrier=span_context)
        span_context_data = json.dumps(span_context)
        metadata[cls.SPAN_METADATA_KEY] = span_context_data

    @classmethod
    def extract_span_context(cls, context: ServicerContext) -> Optional[Context]:
        metadata = context.invocation_metadata()
        if metadata is None:
            return None
        if isinstance(metadata, tuple):
            metadata = Metadata.from_tuple(metadata)
        span_context_data = cast(str, metadata[cls.SPAN_METADATA_KEY])
        if span_context_data is not None:
            span_context_data = cast(Dict, json.loads(span_context_data))
            span_context = TraceContextTextMapPropagator().extract(
                carrier=span_context_data
            )
            return span_context

    @staticmethod
    def status_to_error(
        status: grpc_models.Status, notebook_id: str, plugin_name: str,
    ) -> Optional[errors.BaseError]:
        """
        Convert a grpc Status to a BaseError.

        :param status
        :type status: grpc_models.Status
        :param notebook_id
        :type notebook_id: models.NotebookIdentifier
        :param plugin_name
        :type plugin_name: str
        :return:
        :rtype: Optional[models.BaseError]
        """
        status_code = status.code
        details = status.details
        try:
            if status_code == grpc_models.StatusCode.OK:
                return None
            elif status_code == grpc_models.StatusCode.PLUGIN_NOT_FOUND:
                return errors.PluginNotFound(plugin_name=plugin_name)
            elif status_code == grpc_models.StatusCode.NOTEBOOK_NOT_FOUND:
                return errors.NotebookNotFound(notebook_id=notebook_id)
            elif status_code == grpc_models.StatusCode.BAD_INPUT:
                return errors.BadInput(details=status.details)
            elif status_code == grpc_models.StatusCode.INPUT_SCHEMA_VALIDATION_ERROR:
                validation = errors.SchemaValidationResponse(
                    is_valid=False, error=details
                )
                return errors.InputSchemaValidationError(validation=validation)
            elif status_code == grpc_models.StatusCode.INTERNAL_ERROR:
                return errors.InternalError(details=details)
        except pydantic.ValidationError as e:
            return errors.BadInput(details=str(e))

    @staticmethod
    def error_to_status(error: errors.BaseError) -> grpc_models.Status:
        """
        Convert a BaseError to the appripriate grpc Status.

        :param error:
        :type error: models.BaseError
        :return:
        :rtype: grpc_models.Status
        """
        if isinstance(error, errors.PluginNotFound):
            return grpc_models.Status(
                code=grpc_models.StatusCode.PLUGIN_NOT_FOUND, details=repr(error)
            )
        elif isinstance(error, errors.NotebookNotFound):
            return grpc_models.Status(
                code=grpc_models.StatusCode.NOTEBOOK_NOT_FOUND, details=repr(error),
            )
        elif isinstance(error, errors.InputSchemaValidationError):
            return grpc_models.Status(
                code=grpc_models.StatusCode.INPUT_SCHEMA_VALIDATION_ERROR,
                details=repr(error),
            )
        elif isinstance(error, errors.BadInput):
            return grpc_models.Status(
                code=grpc_models.StatusCode.BAD_INPUT, details=repr(error),
            )
        else:
            # unexcepted error will default to INTERNAL_ERROR
            return grpc_models.Status(
                code=grpc_models.StatusCode.INTERNAL_ERROR, details=repr(error)
            )


class GrpcWorkerServer(grpc_service.WorkerServiceServicer):
    """
    A GrpcServer that wraps a Worker object. Handles the convertion
    between grpc messages and jupyrest.models.
    """

    def __init__(self, worker: Worker) -> None:
        super().__init__()
        self._worker = worker

    async def execute_notebook(
        self, request: grpc_models.NotebookExecutionRequest, context: ServicerContext,
    ) -> grpc_models.NotebookExecutionResponse:
        span_context = GrpcUtils.extract_span_context(context)
        with tracer.start_as_current_span("grpc_request", context=span_context) as t:
            try:
                # parse grpc request
                plugin_name = str(request.plugin_name)
                notebook_id = str(request.notebook_id)

                try:
                    parameters = json.loads(request.parameters.decode("utf-8"))
                except JSONDecodeError as json_e:
                    logger.exception(
                        "An error occurred attempting to convert the parameters bytes into a json string."
                    )
                    return grpc_models.NotebookExecutionResponse(
                        status=grpc_models.Status(
                            code=grpc_models.StatusCode.BAD_INPUT, details=str(json_e),
                        ),
                        notebook=None,
                    )
                parameterize_only = request.parameterize_only

                # execute notebook
                response = await self._worker.execute_notebook_async(
                    plugin_name=plugin_name,
                    notebook_id=notebook_id,
                    parameters=parameters,
                    parameterize_only=parameterize_only,
                )

                if isinstance(response, errors.BaseError):
                    status = GrpcUtils.error_to_status(error=response)
                    return grpc_models.NotebookExecutionResponse(
                        status=status, notebook=None
                    )

                # convert notebook object to bytes
                notebook_data: bytes = nbformat.writes(
                    response, version=4, cls=NbSchemaEncoder,
                ).encode("utf-8")
                notebook = grpc_models.Notebook(ipynb=notebook_data)

                # return response
                status = grpc_models.Status(code=grpc_models.StatusCode.OK, details="")
                return grpc_models.NotebookExecutionResponse(
                    status=status, notebook=notebook
                )

            except Exception as e:
                logger.exception("An unhandled exception occured.")
                status = grpc_models.Status(
                    code=grpc_models.StatusCode.INTERNAL_ERROR, details=str(e),
                )
                return grpc_models.NotebookExecutionResponse(
                    status=status, notebook=None
                )


class GrpcWorkerClient:
    """
    An client adapter for a Worker.
    Wraps a grpc client to communicate with a running GrpcWorkerServer.
    """

    def __init__(
        self, channel: Channel, wait_for_ready: bool = False,
    ):
        super().__init__()
        self.stub = grpc_service.WorkerServiceStub(channel=channel)
        self.wait_for_ready = wait_for_ready

    async def execute_notebook_async(
        self,
        plugin_name: str,
        notebook_id: str,
        parameters: Any,
        parameterize_only=False,
    ) -> Union[errors.BaseError, NotebookNode]:

        with tracer.start_as_current_span("grpc_worker_client"):
            try:
                try:
                    parameter_bytes = json.dumps(parameters).encode("utf-8")
                except TypeError as t:
                    # catch errors when attempting to convert parameters to json string
                    return errors.BadInput(details=str(t))

                grpc_request = grpc_models.NotebookExecutionRequest(
                    notebook_id=notebook_id,
                    plugin_name=plugin_name,
                    parameters=parameter_bytes,
                    parameterize_only=parameterize_only,
                )
                # create a Metadata object and insert
                # the current span context in it
                metadata = Metadata()
                GrpcUtils.inject_span_context(metadata)
                grpc_response = await self.stub.execute_notebook(
                    grpc_request, wait_for_ready=self.wait_for_ready, metadata=metadata
                )
                grpc_response = cast(
                    grpc_models.NotebookExecutionResponse, grpc_response
                )
                if grpc_response.status.code != grpc_models.StatusCode.OK:
                    # return appropriate error is StatusCode != OK
                    error = GrpcUtils.status_to_error(
                        status=grpc_response.status,
                        notebook_id=notebook_id,
                        plugin_name=plugin_name,
                    )
                    if error is not None:
                        return error

                notebook: NotebookNode = nbformat.reads(
                    grpc_response.notebook.ipynb.decode("utf-8"),
                    as_version=nbformat.NO_CONVERT,
                )
                return notebook
            except Exception as e:
                logger.exception("An unhandled exception occurred.")
                return errors.InternalError(details=str(e))
