from ...error import FileObjectNotFound

from ...file_object import FileObject, FileObjectClient
from azure.storage.blob.aio import ContainerClient
from azure.core.exceptions import ResourceNotFoundError

class AzureBlobFileObjectClient(FileObjectClient):

    def __init__(self, container_client: ContainerClient) -> None:
        self.container_client = container_client

    @classmethod
    def get_scheme(cls) -> str:
        return "azure_blob_storage"

    async def get_content(self, file_object: "FileObject") -> str:
        try:
            blob_client = self.container_client.get_blob_client(blob=file_object.path)
            return (await (await blob_client.download_blob()).readall()).decode('utf-8')
        except ResourceNotFoundError as rnfe:
            raise FileObjectNotFound(path=file_object.path) from rnfe

    async def set_content(self, file_object: "FileObject", content: str):
        blob_client = self.container_client.get_blob_client(blob=file_object.path)
        await blob_client.upload_blob(content.encode('utf-8'), overwrite=True)