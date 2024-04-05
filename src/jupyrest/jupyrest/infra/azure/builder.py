from pathlib import Path
from jupyrest.default_impl.builder import ModelSet
from typing import Optional
from ...default_impl.builder import DefaultApplicationBuilder
from .execution_repository import AzureBlobNotebookExecutionRepository
from .file_object_client import AzureBlobFileObjectClient
from .execution_task_handler import AzureQueueNotebookExecutionTaskHandler
from azure.storage.blob.aio import ContainerClient
from azure.storage.queue.aio import QueueClient

class AzureApplicationBuilder(DefaultApplicationBuilder):

    def __init__(self,
            notebooks_dir: Path,
            container_client: ContainerClient,
            queue_client: QueueClient,
            models: Optional[ModelSet] = {}
    ) -> None:
        notebook_execution_repository = AzureBlobNotebookExecutionRepository(container_client=container_client)
        file_object_client = AzureBlobFileObjectClient(container_client=container_client)
        super().__init__(
            notebooks_dir=notebooks_dir,
            notebook_execution_repository=notebook_execution_repository,
            file_object_client=file_object_client,
            models=models)
        self.execution_task_handler = AzureQueueNotebookExecutionTaskHandler(queue_client=queue_client)