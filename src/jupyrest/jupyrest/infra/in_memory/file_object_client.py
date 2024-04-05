from typing import Dict
from ...file_object import FileObjectClient, FileObject
from ...error import FileObjectNotFound

class InMemoryFileObjectClient(FileObjectClient):

    def __init__(self) -> None:
        self._files: Dict[str, str] = {}

    @classmethod
    def get_scheme(cls) -> str:
        return "in_memory"


    async def get_content(self, file_object: "FileObject") -> str:
        try:
            return self._files[file_object.path]
        except KeyError as ke:
            raise FileObjectNotFound(path=file_object.path) from ke

    async def set_content(self, file_object: "FileObject", content: str):
        self._files[file_object.path] = content