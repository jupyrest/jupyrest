from ..value_objects.file_object import FileObject

from nbformat import NotebookNode
from papermill.iorw import load_notebook_node

class Notebook(FileObject):

    async def to_notebook_node(self) -> NotebookNode:
        content = await self.get_content()
        return load_notebook_node(content)

    class Config:
        __ns__ = "jupyrest://value_objects/notebook/v1"

