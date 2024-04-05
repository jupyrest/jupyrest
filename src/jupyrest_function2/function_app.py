import azure.functions as func
import logging
from jupyrest.http.asgi import create_asgi_app
from jupyrest.notebook_execution.commands import complete_execution
from azure.storage.queue.aio import QueueClient
from azure.storage.blob.aio import ContainerClient
from pathlib import Path
import os
import logging
notebooks_dir = Path(__file__).parent / "notebooks"
notebooks_dir = Path("C:\\Users\\Koushik\\code\\jupyrest2\\src\\jupyrest\\tests\\notebooks")
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

from jupyrest.nbschema import NbSchemaBase
from datetime import datetime
class Incident(NbSchemaBase):
    start_time: datetime
    end_time: datetime
    title: str

from jupyrest.infra.azure.builder import AzureApplicationBuilder

builder = AzureApplicationBuilder(
    notebooks_dir=notebooks_dir,
    container_client=container_client,
    queue_client=queue_client,
    models={"incident": Incident})
deps = builder.build()
fastapi_app = create_asgi_app(deps=builder.build())

app = func.AsgiFunctionApp(app=fastapi_app, http_auth_level=func.AuthLevel.ANONYMOUS)

@app.queue_trigger(arg_name="msg", queue_name=queue_name, connection='AzureWebJobsStorage')
async def queue_trigger(msg: func.QueueMessage):
    execution_id = msg.get_body().decode('utf-8')
    logging.info(f"Completing execution: {execution_id}")
    await complete_execution(execution_id=execution_id, deps=deps)