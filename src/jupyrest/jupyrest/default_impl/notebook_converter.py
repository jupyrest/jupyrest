from nbformat import NO_CONVERT, writes
from nbformat.notebooknode import NotebookNode
from nbconvert import HTMLExporter


from ..contracts import NotebookConverter
from ..nbschema import NbSchemaEncoder

class DefaultNotebookConverter(NotebookConverter):

    def convert_notebook_to_html(self,
                                notebook: NotebookNode,
                                report_mode: bool) -> str:
        exporter = HTMLExporter()
        if report_mode:
            exporter = HTMLExporter(exclude_output_prompt=True, exclude_input=True)
        (body, _) = exporter.from_notebook_node(notebook)
        return body


    def convert_notebook_to_str(self, notebook: NotebookNode) -> str:
        return writes(
            notebook, version=NO_CONVERT, cls=NbSchemaEncoder
        )