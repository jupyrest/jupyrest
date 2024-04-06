from abc import ABC, abstractmethod

from .model import NamedModel

class FileObjectClient(ABC):

    @classmethod
    @abstractmethod
    def get_scheme(cls) -> str:
        pass


    @abstractmethod
    async def get_content(self, file_object: "FileObject") -> str:
        pass

    @abstractmethod
    async def set_content(self, file_object: "FileObject", content: str):
        pass

    def new_file_object(self, path: str) -> "FileObject":
        return FileObject(path=path, scheme=self.get_scheme())

class FileObject(NamedModel):
    path: str
    scheme: str

    class Config:
        __ns__ = "jupyrest.FileObject"