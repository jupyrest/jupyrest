import azure.functions as func
import datetime
import json
import logging
from jupyrest.workers.http import create_azure_function, create_dev_app
from jupyrest.plugin import JupyrestPlugin
from jupyrest.resolvers import LocalDirectoryResolver
from jupyrest.nbschema import NotebookSchemaProcessor
from jupyrest.executors import IPythonNotebookExecutor
from jupyrest.workers.http import InMemoryNotebookEventStoreRepository
from jupyrest.workers.base import Worker
from jupyrest.plugin import PluginManager

from pathlib import Path

notebooks_dir = Path(__file__).parent / "notebooks"

plugin_man = PluginManager()
plugin = JupyrestPlugin(
    resolver=LocalDirectoryResolver(notebooks_dir=notebooks_dir),
    nbschema=NotebookSchemaProcessor(),
    executor=IPythonNotebookExecutor(),
)
plugin_man.register(plugin_name=PluginManager.DEFAULT_PLUGIN_NAME, plugin=plugin)

worker = Worker(plugin_man=plugin_man)
fastapi_app = create_dev_app(worker=worker, event_store_repository=InMemoryNotebookEventStoreRepository())

function_app = create_azure_function(fastapi_app=fastapi_app)

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)

@app.queue_trigger(arg_name="msg", queue_name='myqueue', connection='AzureWebJobsStorage')
def queue_trigger(msg: func.QueueMessage):
    logging.info(f"Python queue trigger function processed a queue item: {msg.get_body().decode('utf-8')}")