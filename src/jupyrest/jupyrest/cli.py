from jupyrest.workers.base import Worker
from jupyrest.executors import IPythonNotebookExecutor
from jupyrest.nbschema import NotebookSchemaProcessor
from jupyrest.resolvers import LocalDirectoryResolver
import typer
from enum import Enum
from typing import Optional
from pathlib import Path
from jupyrest.plugin import PluginManager, JupyrestPlugin
from jupyrest.workers.grpc import GrpcWorkerServer
from jupyrest.workers.http import create_dev_app
from jupyrest.workers.generated import jupyrest_pb2_grpc
import grpc
import asyncio
import uvicorn
import logging
from opentelemetry import trace


class WorkerType(str, Enum):
    grpc = "grpc"
    http = "http"


HTTP_PORT = 5050
GRPC_PORT = 50051
MAX_MESSAGE_LENGTH = 100 * 1024 * 1024  # 100 MB

cli_app = typer.Typer(name="jupyrest cli")
worker_app = typer.Typer()

cli_app.add_typer(worker_app, name="worker")


async def serve_grpc(worker: Worker, port: int):

    server = grpc.aio.server(
        options=[
            ("grpc.max_send_message_length", MAX_MESSAGE_LENGTH),
            ("grpc.max_receive_message_length", MAX_MESSAGE_LENGTH),
        ]
    )
    jupyrest_pb2_grpc.add_WorkerServiceServicer_to_server(
        GrpcWorkerServer(worker), server
    )
    listen_addr = f"[::]:{port}"
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span("start grpc server"):
        server.add_insecure_port(listen_addr)
        logging.info(f"Starting grpc worker server on {listen_addr}")
        await server.start()
        try:
            await server.wait_for_termination()
        except KeyboardInterrupt:
            # Shuts down the server with 0 seconds of grace period. During the
            # grace period, the server won't accept new connections and allow
            # existing RPCs to continue within the grace period.
            await server.stop(0)


@worker_app.command("start")
def start(
    worker_type: WorkerType,
    notebooks_dir: Optional[Path] = typer.Option(None),
    port: Optional[int] = typer.Option(None, help="Port to serve worker on."),
    fluentd: bool = False,
):

    plugin_man = PluginManager()
    if notebooks_dir is not None:
        plugin_man.register(
            plugin_name=PluginManager.DEFAULT_PLUGIN_NAME,
            plugin=JupyrestPlugin(
                resolver=LocalDirectoryResolver(notebooks_dir=notebooks_dir),
                nbschema=NotebookSchemaProcessor(),
                executor=IPythonNotebookExecutor(),
            ),
        )
    worker = Worker(plugin_man=plugin_man)

    if worker_type == WorkerType.grpc:
        if port is None:
            port = GRPC_PORT
        loop = asyncio.get_event_loop()
        coro = serve_grpc(worker=worker, port=port)
        loop.run_until_complete(coro)

    elif worker_type == WorkerType.http:
        if port is None:
            port = HTTP_PORT
        http_app = create_dev_app(worker=worker)
        typer.echo(f"Starting http worker server on {port}")
        uvicorn.run(app=http_app, port=port)  # type: ignore
