from pydantic import BaseModel, Field
from typing import Optional, Dict, Protocol, Iterable
from nbformat.notebooknode import NotebookNode
from papermill.iorw import load_notebook_node


class NotebookConfigFile(BaseModel):
    id: Optional[str] = None
    input: Dict = {}
    output: Dict = {}


class NotebookConfig(BaseModel):
    id: str
    notebook_path: str
    input: Dict = {}
    output: Dict = {}
    resolved_input_schema: Dict = {}
    resolved_output_schema: Dict = {}

    def load_notebook_node(self) -> NotebookNode:
        return load_notebook_node(notebook_path=self.notebook_path)