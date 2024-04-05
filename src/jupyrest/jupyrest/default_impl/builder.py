from ..contracts import ApplicationBuilder, FileObjectClient, NotebookConverter, DependencyBag
from ..nbschema import NbSchemaBase, NotebookSchemaProcessor
from ..contracts import (
    NotebookExecutionRepository,
    NotebookRepository,
    FileObjectClient,
    NotebookConverter,
    NotebookParameterizier,
    NotebookExeuctor,
    NotebookOutputReader,
    NotebookInputOutputValidator,
    NotebookExecutionTaskHandler,
    NotebookExecutionFileNamer
)

from .execution_task_handler import DefaultNotebookExecutionTaskHandler
from .executor import IPythonNotebookExecutor
from .file_namer import DefaultNotebookExecutionFileNamer
from .output_reader import DefaultNotebookOutputReader
from .parameterizer import DefaultNotebookParameterizier
from .notebook_converter import DefaultNotebookConverter
from .notebook_repository import DefaultNotebookRepository
from .input_output_validator import DefaultNotebookInputOutputValidator

from pathlib import Path
from typing import Dict, Type, Optional

ModelSet = Dict[str, Type[NbSchemaBase]]

class DefaultApplicationBuilder(ApplicationBuilder):

    def __init__(self,
                notebooks_dir: Path,
                notebook_execution_repository: NotebookExecutionRepository,
                file_object_client: FileObjectClient,
                models: Optional[ModelSet] = None) -> None:
        self.notebooks_dir = notebooks_dir
        self.models = models or {}
        self.nbschema = NotebookSchemaProcessor(models=self.models)

        self.notebook_execution_repository = notebook_execution_repository
        self.file_obj_client = file_object_client

        self.notebook_converter: NotebookConverter = DefaultNotebookConverter()
        self.notebook_executor: NotebookExeuctor = IPythonNotebookExecutor()
        self.notebook_parameterizier: NotebookParameterizier = DefaultNotebookParameterizier(nbschema=self.nbschema, kernelspec_language=self.notebook_executor.get_kernelspec_language())
        self.notebook_output_reader: NotebookOutputReader = DefaultNotebookOutputReader(nbschema=self.nbschema)
        self.notebook_input_output_validator: NotebookInputOutputValidator = DefaultNotebookInputOutputValidator(nbschema=self.nbschema)
        self.notebook_execution_task_handler: NotebookExecutionTaskHandler = DefaultNotebookExecutionTaskHandler()
        self.notebook_execution_file_namer: NotebookExecutionFileNamer = DefaultNotebookExecutionFileNamer()
        self.notebook_repository: NotebookRepository = DefaultNotebookRepository(notebooks_dir=self.notebooks_dir, nbschema=self.nbschema)

    def build(self) -> DependencyBag:
        return DependencyBag(
            notebook_execution_repository=self.notebook_execution_repository,
            notebook_repository=self.notebook_repository,
            file_obj_client=self.file_obj_client,
            notebook_converter=self.notebook_converter,
            notebook_parameterizier=self.notebook_parameterizier,
            notebook_executor=self.notebook_executor,
            notebook_output_reader=self.notebook_output_reader,
            notebook_input_output_validator=self.notebook_input_output_validator,
            notebook_execution_task_handler=self.notebook_execution_task_handler,
            notebook_execution_file_namer=self.notebook_execution_file_namer,
        )