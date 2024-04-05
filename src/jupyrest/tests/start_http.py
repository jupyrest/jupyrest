from pathlib import Path
import uvicorn
from jupyrest.default_impl.executor import IPythonNotebookExecutor
from jupyrest.nbschema import NotebookSchemaProcessor, ModelCollection, NbSchemaBase
from jupyrest.infra.in_memory.builder import InMemoryApplicationBuilder
from datetime import datetime
from jupyrest.http.asgi import create_asgi_app
import logging

logging.basicConfig(level=logging.DEBUG)

class Incident(NbSchemaBase):
    start_time: datetime
    end_time: datetime
    title: str


def start_http_server():
    notebooks_dir = Path(__file__).parent / "notebooks"
    builder = InMemoryApplicationBuilder(notebooks_dir=notebooks_dir, models={"incident": Incident})

    asgi_app = create_asgi_app(deps=builder.build())
    import sys
    import asyncio

    if sys.platform == "win32":
        loop = asyncio.ProactorEventLoop()
        asyncio.set_event_loop(loop)
    uvicorn.run(app=asgi_app, port=5050)  # type: ignore


if __name__ == "__main__":
    start_http_server()
