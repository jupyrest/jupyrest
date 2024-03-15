from abc import ABC, abstractmethod
from typing_extensions import Self
from ..model import NamedModel

class FileObject(NamedModel, ABC):
    path: str

    @classmethod
    @abstractmethod
    async def create(cls, path: str, content: str) -> Self:
        pass

    @abstractmethod
    async def get_content(self) -> str:
        pass

    @abstractmethod
    async def set_content(self, content: str):
        pass

class NonExistentFileObject(FileObject):

    async def get_content(self) -> str:
        raise FileNotFound()

    async def set_content(self, content: str):
        raise FileNotFound()

    class Config:
        __ns__ = "jupyrest.file_io.core.EmptyFileObject"

class FileNotFound(Exception):
    pass