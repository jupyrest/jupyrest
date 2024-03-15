from abc import ABC, abstractmethod
from anyio import Path
from jupyrest.model import NamedModel

class FileObject(NamedModel, ABC):
    path: str

    @abstractmethod
    async def get_content(self) -> str:
        pass

    @abstractmethod
    async def set_content(self, content: str):
        pass

    class Config:
        __ns__ = "jupyrest.iorw.file_object://v1"

class LocalFileObject(FileObject):

    async def get_content(self) -> str:
        return await Path(self.path).read_text()
        
    async def set_content(self, content: str):
        await Path(self.path).write_text(content)

    class Config:
        __ns__ = "jupyrest.iorw.local_file_object://v1"