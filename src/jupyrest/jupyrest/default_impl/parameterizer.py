from copy import deepcopy
from typing import Dict, Any

from papermill.parameterize import parameterize_notebook as papermill_parameterize_notebook
from nbformat.notebooknode import NotebookNode

from ..contracts import NotebookParameterizier
from ..nbschema import NotebookSchemaProcessor
from ..notebook_config import NotebookConfig


class DefaultNotebookParameterizier(NotebookParameterizier):

    def __init__(self, nbschema: NotebookSchemaProcessor, kernelspec_language: str) -> None:
        self.nbschema = nbschema
        self.kernelspec_language = kernelspec_language

    def parameterize_notebook(
        self, notebook_config: NotebookConfig, parameters: Dict[str, Any]
    ) -> NotebookNode:
        parameters_copy = deepcopy(parameters)
        input_schema = notebook_config.input
        parameters_copy = self.nbschema.inject_model_refs(input_schema, parameters_copy)
        notebook = notebook_config.load_notebook_node()
        # Parameterize notebooks with papermill, then fix it so it can work in jupyrest
        if "language" not in notebook.metadata.kernelspec:
            notebook.metadata.kernelspec["language"] = self.kernelspec_language
        # Papermill will do a deepcopy of the input notebook and
        # return the copy with the parameter cell
        new_notebook = papermill_parameterize_notebook(nb=notebook, parameters=parameters_copy)
        # Fix papermill's parameters metadata.
        # We reset the parameters to the original parameters prior to inject_model_refs
        new_notebook.metadata.papermill.parameters = parameters
        return new_notebook