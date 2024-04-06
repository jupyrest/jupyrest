from ...contracts import NotebookExecutionRepository
from azure.storage.blob.aio import ContainerClient
from azure.core.exceptions import ResourceNotFoundError
from ...notebook_execution.entity import NotebookExecution
from ...error import NotebookExecutionNotFound

class AzureBlobNotebookExecutionRepository(NotebookExecutionRepository):

    def __init__(self, container_client: ContainerClient) -> None:
        self.container_client = container_client

    def _get_blob_name(self, execution_id: str) -> str:
        return f"{execution_id}.execution.json"

    async def get(self, execution_id: str) -> NotebookExecution:
        try:
            blob_name = self._get_blob_name(execution_id)
            blob_client = self.container_client.get_blob_client(blob=blob_name)
            blob_data = await (await blob_client.download_blob()).readall()
            return NotebookExecution.parse_raw(blob_data)
        except ResourceNotFoundError as rnfe:
            raise NotebookExecutionNotFound(execution_id=execution_id) from rnfe
        
    async def save(self, execution: NotebookExecution) -> None:
        blob_name = self._get_blob_name(execution.execution_id)
        blob_client = self.container_client.get_blob_client(blob=blob_name)
        await blob_client.upload_blob(execution.json(), overwrite=True)

    async def create(self, execution: NotebookExecution) -> None:
        blob_name = self._get_blob_name(execution.execution_id)
        blob_client = self.container_client.get_blob_client(blob=blob_name)
        await blob_client.upload_blob(execution.json())
