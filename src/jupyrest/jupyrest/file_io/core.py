from abc import ABC, abstractmethod
from enum import Enum
from ..model import NamedModel
from typing import Dict
from ..errors2 import UnrecognizedFileObjectScheme, FileObjectNotFound

class FileObjectScheme(str, Enum):
    IN_MEMORY = "in_memory"

class FileObjectClientImpl(ABC):

    @abstractmethod
    async def get_content(self, path: str) -> str:
        pass

    @abstractmethod
    async def set_content(self, path: str, content: str):
        pass

class FileObjectClient:

    def __init__(self, client_map: Dict[str, FileObjectClientImpl], default_scheme = FileObjectScheme.IN_MEMORY) -> None:
        self.client_map = client_map
        self.default_scheme = default_scheme

    def get_impl(self, scheme: str) -> FileObjectClientImpl:
        try:
            return self.client_map[scheme]
        except KeyError as ke:
            raise UnrecognizedFileObjectScheme(scheme=scheme) from ke

    async def get_content(self, file_object: "FileObject") -> str:
        try:
            return await self.get_impl(file_object.scheme).get_content(file_object.path)
        except FileNotFound as fnf:
            raise FileObjectNotFound(path=f"{file_object.schema}://{file_object.path}") from fnf

    async def set_content(self, file_object: "FileObject", content: str):
        await self.get_impl(file_object.scheme).set_content(file_object.path, content)
    
    def new_file_object(self, path: str) -> "FileObject":
        return FileObject(path=path, scheme=self.default_scheme)

class FileObject(NamedModel):
    path: str
    scheme: FileObjectScheme

    class Config:
        __ns__ = "jupyrest.FileObject"

class FileNotFound(Exception):
    pass