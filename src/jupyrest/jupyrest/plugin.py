from nbformat.notebooknode import NotebookNode
from .resolvers import BaseResolver, NotebookConfig
from .nbschema import NotebookSchemaProcessor, SchemaValidationResponse
from .executors import BaseNotebookExeuctor
from typing import Optional, Dict, Type, Any
from abc import ABC, abstractmethod
import entrypoints
from papermill.parameterize import parameterize_notebook
from copy import deepcopy
import logging
import json

logger = logging.getLogger(__name__)


class BasePlugin(ABC):
    """
    Contract for a Plugin.
    """

    @abstractmethod
    def parameterize_notebook(
        self, notebook_id: str, parameters: Any, notebook: NotebookNode
    ) -> NotebookNode:
        pass

    @abstractmethod
    def get_notebook_executor(self) -> BaseNotebookExeuctor:
        pass

    @abstractmethod
    def get_resolver(self) -> BaseResolver:
        pass

    @abstractmethod
    def get_nbschema(self) -> NotebookSchemaProcessor:
        pass

    @abstractmethod
    def validate_input(
        self, notebook_id: str, parameters: Any
    ) -> SchemaValidationResponse:
        pass

    @abstractmethod
    def validate_output(
        self, notebook_id: str, output: str
    ) -> SchemaValidationResponse:
        pass

    @abstractmethod
    def get_input_schema(self, notebook_id: str) -> Dict:
        ...

    @abstractmethod
    def get_output_schema(self, notebook_id: str) -> Dict:
        ...


class PluginManager:

    DEFAULT_PLUGIN_NAME = "default"
    _plugins: Dict[str, BasePlugin] = {}

    def __init__(self) -> None:
        self.register_entry_points()

    def _get_plugin(self, plugin_name: str) -> Optional[BasePlugin]:
        return self._plugins.get(plugin_name, None)

    def register(self, plugin_name: str, plugin: BasePlugin):
        self._plugins[plugin_name] = plugin

    def register_entry_points(self):
        for entrypoint in entrypoints.get_group_all("jupyrest.plugins"):
            name = str(entrypoint.name)
            try:
                plugin: BasePlugin = entrypoint.load()
            except:
                logger.exception(f"Failed to load plugin {name}.")
            else:
                self.register(plugin_name=name, plugin=plugin)

    def load(self, plugin_name: str) -> Optional[BasePlugin]:
        plugin = self._get_plugin(plugin_name=plugin_name)
        if plugin is not None:
            return plugin
        else:
            return None


class JupyrestPlugin(BasePlugin):
    def __init__(
        self,
        resolver: BaseResolver,
        nbschema: NotebookSchemaProcessor,
        executor: BaseNotebookExeuctor,
    ) -> None:
        self._resolver = resolver
        self._nbschema = nbschema
        self._executor = executor

    def get_resolver(self) -> BaseResolver:
        return self._resolver

    def get_nbschema(self) -> NotebookSchemaProcessor:
        return self._nbschema

    def get_notebook_executor(self) -> BaseNotebookExeuctor:
        return self._executor

    def parameterize_notebook(
        self, notebook_id: str, parameters: Any, notebook: NotebookNode
    ) -> NotebookNode:
        config = self.get_resolver().resolve_config(notebook_id=notebook_id)
        parameters_copy = deepcopy(parameters)
        input_schema = config.input
        parameters_copy = self.get_nbschema().inject_model_refs(
            input_schema, parameters_copy
        )
        # Parameterize notebooks with papermill, then fix it so it can work in jupyrest
        if "language" not in notebook.metadata.kernelspec:
            notebook.metadata.kernelspec[
                "language"
            ] = self.get_notebook_executor().get_kernelspec_language()
        # Papermill will do a deepcopy of the input notebook and
        # return the copy with the parameter cell
        new_notebook = parameterize_notebook(nb=notebook, parameters=parameters_copy)
        # Fix papermill's parameters metadata.
        # We reset the parameters to the original parameters prior to inject_model_refs
        new_notebook.metadata.papermill.parameters = parameters
        return new_notebook

    def get_input_schema(self, notebook_id: str) -> Dict:
        config = self.get_resolver().resolve_config(notebook_id=notebook_id)
        if config.resolved_input_schema is None:
            config.resolved_input_schema = self.get_nbschema().fix_schemas(
                schema=config.input, add_model_definitions=True
            )
        return config.resolved_input_schema

    def get_output_schema(self, notebook_id: str) -> Dict:
        config = self.get_resolver().resolve_config(notebook_id=notebook_id)
        if config.resolved_output_schema is None:
            config.resolved_output_schema = self.get_nbschema().fix_schemas(
                schema=config.output, add_model_definitions=True
            )
        return config.resolved_output_schema

    def validate_input(
        self, notebook_id: str, parameters: Any
    ) -> SchemaValidationResponse:
        input_schema = self.get_input_schema(notebook_id=notebook_id)
        return self.get_nbschema().validate_instance(
            instance=parameters, schema=input_schema
        )

    def validate_output(
        self, notebook_id: str, output: str
    ) -> SchemaValidationResponse:
        output_schema = self.get_output_schema(notebook_id=notebook_id)
        return self._nbschema.validate_instance(
            instance=json.loads(output), schema=output_schema
        )
