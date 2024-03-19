from typing import Dict

from .core import FileObjectClientImpl, FileNotFound


class InMemoryFileObjectClientImpl(FileObjectClientImpl):

    def __init__(self) -> None:
        self._files: Dict[str, str] = {}

    async def get_content(self, path: str) -> str:
        try:
            return self._files[path]
        except KeyError as ke:
            raise FileNotFound() from ke

    async def set_content(self, path: str, content: str):
        self._files[path] = content