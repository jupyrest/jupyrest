import azure.functions as func
import logging
from fastapi import dependencies
from jupyrest.dependencies import Dependencies
from jupyrest.azure.execution_task_handler import AzureQueueNotebookExecutionTaskHandler
from jupyrest.http.asgi import create_asgi_app
from jupyrest.notebook_execution.commands import complete_execution
from azure.storage.queue.aio import QueueClient
from azure.storage.blob.aio import ContainerClient
from azure.core.exceptions import ResourceExistsError
from pathlib import Path
import os
import logging
notebooks_dir = Path(__file__).parent / "notebooks"
container_name = "jupyrest-executions"
container_client = ContainerClient.from_connection_string(
    conn_str=os.environ["AzureWebJobsStorage"],
    container_name=container_name
)
queue_name = "jupyrest-executions"
queue_client = QueueClient.from_connection_string(
    conn_str=os.environ["AzureWebJobsStorage"],
    queue_name=queue_name
)
dependencies = Dependencies(
    notebooks_dir=notebooks_dir,
    models={}
).get_azure_dependency_bag(container_client=container_client, queue_client=queue_client)
fastapi_app = create_asgi_app(deps=dependencies)

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)

@app.queue_trigger(arg_name="msg", queue_name=queue_name, connection='AzureWebJobsStorage')
async def queue_trigger(msg: func.QueueMessage):
    try:
        message = AzureQueueNotebookExecutionTaskHandler.deserialize_message(msg.get_json())
        await complete_execution(execution_id=message.execution_id, deps=dependencies)
    except Exception as e:
        logging.exception("An error occurred while processing a queue message.")