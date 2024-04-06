from ..contracts import NotebookOutputReader
from ..nbschema import NotebookSchemaProcessor, OutputResult
from nbformat.notebooknode import NotebookNode

class DefaultNotebookOutputReader(NotebookOutputReader):

    def __init__(self, nbschema: NotebookSchemaProcessor) -> None:
        self.nbschema = nbschema

    def get_output(self, notebook: NotebookNode) -> OutputResult:
        return self.nbschema.get_notebook_output(notebook=notebook)