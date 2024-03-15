from abc import ABC, abstractmethod
from logging import config
from pydoc import resolve
from typing import Dict, Type, Any, AsyncIterable
from pathlib import Path
from copy import deepcopy
from .plugin import PluginManager, JupyrestPlugin
from .nbschema import (
    NbSchemaBase,
    NotebookSchemaProcessor,
    ModelCollection,
    SchemaValidationResponse,
    NbSchemaEncoder,
    OutputResult
)
from .resolvers import LocalDirectoryResolver, NotebookConfigFile
from .executors import IPythonNotebookExecutor, BaseNotebookExeuctor
from dataclasses import dataclass
from .contracts import (
    NotebookExecutionRepository,
    NotebookConverter,
    NotebookParameterizier,
    NotebookOutputReader,
    NotebookInputOutputValidator,
    NotebookExecutionTaskHandler,
    NotebookRepository,
    NotebookExecutionFileNamer,
    DependencyBag
)
from .file_io.in_memory import InMemoryFileObject
from .notebook_execution.entity import NotebookExecution
from .notebook_execution.commands import complete_execution
from .notebook_config import NotebookConfig
from nbformat.notebooknode import NotebookNode
from nbconvert import HTMLExporter
import nbformat
from papermill.parameterize import parameterize_notebook as papermill_parameterize_notebook
from .errors2 import NotebookExecutionNotFound, NotebookNotFound
import json

class InMemoryNotebookExecutionRepository(NotebookExecutionRepository):
    def __init__(self) -> None:
        self._executions: Dict[str, NotebookExecution] = {}

    async def get(self, execution_id: str) -> NotebookExecution:
        try:
            return self._executions[execution_id]
        except KeyError:
            raise NotebookExecutionNotFound(execution_id=execution_id)

    async def save(self, execution: NotebookExecution) -> None:
        self._executions[execution.execution_id] = execution

    async def create(self, execution: NotebookExecution) -> None:
        self._executions[execution.execution_id] = execution

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
        return nbformat.writes(
            notebook, version=nbformat.NO_CONVERT, cls=NbSchemaEncoder
        )
    
class DefaultNotebookParameterizier(NotebookParameterizier):

    def __init__(self, plugin: JupyrestPlugin) -> None:
        self.plugin = plugin

    def parameterize_notebook(
        self, notebook_config: NotebookConfig, parameters: Dict[str, Any]
    ) -> NotebookNode:
        parameters_copy = deepcopy(parameters)
        input_schema = notebook_config.input
        parameters_copy = self.plugin.get_nbschema().inject_model_refs(
            input_schema, parameters_copy
        )
        notebook = notebook_config.load_notebook_node()
        # Parameterize notebooks with papermill, then fix it so it can work in jupyrest
        if "language" not in notebook.metadata.kernelspec:
            notebook.metadata.kernelspec[
                "language"
            ] = self.plugin.get_notebook_executor().get_kernelspec_language()
        # Papermill will do a deepcopy of the input notebook and
        # return the copy with the parameter cell
        new_notebook = papermill_parameterize_notebook(nb=notebook, parameters=parameters_copy)
        # Fix papermill's parameters metadata.
        # We reset the parameters to the original parameters prior to inject_model_refs
        new_notebook.metadata.papermill.parameters = parameters
        return new_notebook
    
class DefaultNotebookOutputReader(NotebookOutputReader):

    def __init__(self, plugin: JupyrestPlugin) -> None:
        self.plugin = plugin

    def get_output(self, notebook: NotebookNode) -> OutputResult:
        return self.plugin.get_nbschema().get_notebook_output(notebook=notebook)
    
class DefaultNotebookInputOutputValidator(NotebookInputOutputValidator):
    
    def __init__(self, plugin: JupyrestPlugin) -> None:
        self.plugin = plugin

    def validate_input(
        self, notebook_config: NotebookConfig, parameters: Dict[str, Any]
    ) -> SchemaValidationResponse:
        return self.plugin.get_nbschema().validate_instance(instance=parameters, schema=notebook_config.input)

    def validate_output(
        self, notebook_config: NotebookConfig, output: str
    ) -> SchemaValidationResponse:
        return self.plugin.get_nbschema().validate_instance(instance=json.loads(output), schema=notebook_config.output)
    
class DefaultNotebookExecutionTaskHandler(NotebookExecutionTaskHandler):

    def __init__(self, plugin: JupyrestPlugin) -> None:
        self.plugin = plugin

    async def submit_execution_task(
        self,
        execution_id: str,
        deps: "DependencyBag",
    ):
        execution = await deps.notebook_execution_repository.get(
            execution_id=execution_id
        )
        await complete_execution(execution=execution, deps=deps)

class DefaultNotebookRepository(NotebookRepository):

    def __init__(self, notebooks_dir: Path, nbschema: NotebookSchemaProcessor) -> None:
        if not notebooks_dir.exists() or not notebooks_dir.is_dir():
            raise ValueError(f"{notebooks_dir} needs to be a valid directory")
        self.notebooks_dir = notebooks_dir
        self.nbschema = nbschema
        self._configs: Dict[str, NotebookConfig] = {}
        self.refresh()

    def refresh(self):
        self._configs.clear()
        config_paths = list(self.notebooks_dir.glob("**/*.config.json"))
        for config_path in config_paths:
            notebook_path = self.get_notebook_path_from_config_path(
                config_path=config_path
            )
            if notebook_path.exists() and notebook_path.is_file():
                notebook_config = self.notebook_config_from_file(
                    config_path=config_path
                )
                self._configs[notebook_config.id] = notebook_config

    def get_notebook_path_from_config_path(self, config_path: Path) -> Path:
        return Path(str(config_path).replace(".config.json", ".ipynb"))

    def notebook_config_from_file(self, config_path: Path) -> NotebookConfig:
        notebook_path = self.get_notebook_path_from_config_path(config_path=config_path)
        notebook_config_file = NotebookConfigFile.parse_raw(config_path.read_text())
        notebook_id = (
            notebook_config_file.id
            or notebook_path.relative_to(self.notebooks_dir).as_posix().removesuffix(".ipynb")
        )
        resolved_input = self.nbschema.fix_schemas(schema=notebook_config_file.input, add_model_definitions=True)
        resolved_output = self.nbschema.fix_schemas(schema=notebook_config_file.output, add_model_definitions=True)
        notebook_config = NotebookConfig(
            id=notebook_id,
            notebook_path=notebook_path.as_posix(),
            input=notebook_config_file.input,
            output=notebook_config_file.output,
            resolved_input_schema=resolved_input,
            resolved_output_schema=resolved_output
        )
        return notebook_config

    async def get(self, notebook_id: str) -> NotebookConfig:
        if notebook_id in self._configs:
            return self._configs[notebook_id]
        else:
            raise NotebookNotFound(notebook_id=notebook_id) 

    async def iter_notebook_ids(self) -> AsyncIterable[str]:
        for notebook_id in self._configs.keys():
            yield notebook_id

class DefaultNotebookExecutionFileNamer(NotebookExecutionFileNamer):

    def get_ipynb_name(self, execution: NotebookExecution) -> str:
        return f"{execution.execution_id}.ipynb"
    
    def get_html_name(self, execution: NotebookExecution) -> str:
        return f"{execution.execution_id}.html"
    
    def get_html_report_name(self, execution: NotebookExecution) -> str:
        return f"{execution.execution_id}.report.html"

class Dependencies:
    def __init__(
        self, notebooks_dir: Path, models: Dict[str, Type[NbSchemaBase]]
    ) -> None:
        self.notebooks_dir = notebooks_dir
        self.plugin_manager = PluginManager()
        model_collection = ModelCollection()
        for model_alias, model_type in models.items():
            model_collection.add_model(alias=model_alias, model_type=model_type)
        self.nbschema = NotebookSchemaProcessor(models=model_collection)
        self.plugin = JupyrestPlugin(
                resolver=LocalDirectoryResolver(notebooks_dir=notebooks_dir),
                executor=IPythonNotebookExecutor(),
                nbschema=self.nbschema,
            )
        self.plugin_manager.register(
            plugin_name=PluginManager.DEFAULT_PLUGIN_NAME,
            plugin=self.plugin,
        )
    
    def get_dependency_bag(self) -> DependencyBag:
        return DependencyBag(
            notebook_execution_repository=InMemoryNotebookExecutionRepository(),
            notebook_repository=DefaultNotebookRepository(notebooks_dir=self.notebooks_dir, nbschema=self.nbschema),
            file_obj=InMemoryFileObject,
            notebook_converter=DefaultNotebookConverter(),
            notebook_parameterizier=DefaultNotebookParameterizier(plugin=self.plugin),
            notebook_executor=self.plugin.get_notebook_executor(),
            notebook_output_reader=DefaultNotebookOutputReader(plugin=self.plugin),
            notebook_input_output_validator=DefaultNotebookInputOutputValidator(plugin=self.plugin),
            notebook_execution_task_handler=DefaultNotebookExecutionTaskHandler(plugin=self.plugin),
            notebook_execution_file_namer=DefaultNotebookExecutionFileNamer()
        )