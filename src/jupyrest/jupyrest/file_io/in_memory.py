from typing import Dict

from .core import FileObject, FileNotFound
from ..errors2 import NotebookExecutionArtifactNotFound
from ..contracts import DependencyBag

_files: Dict[str, str] = {}

class InMemoryFileObject(FileObject):

    async def get_content(self, deps: DependencyBag) -> str:
        global _files
        try:
            return _files[self.path]
        except KeyError as ke:
            raise FileNotFound() from ke

    async def set_content(self, deps: DependencyBag, content: str):
        global _files
        _files[self.path] = content

    class Config:
        __ns__ = "jupyrest.InMemoryFileObject"