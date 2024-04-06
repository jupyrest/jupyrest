from ...contracts import NotebookExecutionTaskHandler, DependencyBag
from azure.storage.queue.aio import QueueClient
import base64

class AzureQueueNotebookExecutionTaskHandler(NotebookExecutionTaskHandler):

    def __init__(self, queue_client: QueueClient) -> None:
        self.queue_client = queue_client

    @classmethod
    def serialize_message(cls, execution_id: str):
        return execution_id

    @classmethod
    def deserialize_message(cls, message):
        return None

    async def submit_execution_task(self, execution_id: str, deps: "DependencyBag"):
        base64_message = base64.b64encode(execution_id.encode()).decode()
        await self.queue_client.send_message(base64_message)