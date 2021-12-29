from datetime import datetime
from jupyrest.nbschema import SchemaValidationResponse
from jupyrest.workers.generated.jupyrest_pb2 import Notebook
import logging
from logging import Logger
import json
from nbformat.notebooknode import NotebookNode
from jupyrest.domain import (
    NotebookEventStore,
    NotebookExecutionCreated,
    NotebookExecuted,
)
from typing import Any, Dict, Optional, Union, MutableMapping, Mapping
from uuid import uuid4
from jupyrest.errors import (
    BadInput,
    BaseError,
    PluginNotFound,
    InputSchemaValidationError,
    NotebookNotFound,
)
from jupyrest.plugin import PluginManager

logger = logging.getLogger(__name__)


class ExecuteNotebookLogAdapter(logging.LoggerAdapter):
    def process(self, msg, kwargs):
        plugin_name = f'plugin_name={self.extra["plugin_name"]!r}'
        notebook_id = f'notebook_id={self.extra["notebook_id"]!r}'
        parameterize_only = f'parameterize_only={self.extra["parameterize_only"]!r}'
        context = "ExecuteNotebookInfo[{}, {}, {}]".format(
            plugin_name, notebook_id, parameterize_only
        )
        return f"{context} {msg}", kwargs


class Worker:
    """
    A Worker orchestrates the execution of notebooks and the retrieval of their outputs.
    """

    def __init__(self, plugin_man: PluginManager):
        self.plugin_man = plugin_man

    async def execute_notebook_async(
        self,
        plugin_name: str,
        notebook_id: str,
        parameters: Dict,
        parameterize_only: bool = False,
    ) -> Union[BaseError, NotebookNode]:
        # check args
        if not isinstance(plugin_name, str):
            return BadInput(details=f"invalid plugin_name parameter {plugin_name}")
        if not isinstance(notebook_id, str):
            return BadInput(details=f"invalid notebook_id parameter {notebook_id}")
        if not isinstance(parameterize_only, bool):
            return BadInput(
                details=f"parameterize_only is not of type bool, parameterize_only={parameterize_only}"
            )

        context = {
            "plugin_name": plugin_name,
            "notebook_id": notebook_id,
            "parameterize_only": parameterize_only,
        }
        log = ExecuteNotebookLogAdapter(logger, extra=context)

        # validate plugin exists
        plugin = self.plugin_man.load(plugin_name=plugin_name)
        if plugin is None:
            return PluginNotFound(plugin_name=plugin_name)
        log.info(f"Loaded plugin {plugin_name}")
        # validate notebook exists
        notebook = plugin.get_resolver().resolve_notebook(notebook_id=notebook_id)
        if notebook is None:
            return NotebookNotFound(notebook_id=notebook_id)

        # validate parameters and schema
        input_schema_validation = plugin.validate_input(
            notebook_id=notebook_id, parameters=parameters
        )
        if not input_schema_validation.is_valid:
            return InputSchemaValidationError(validation=input_schema_validation)

        notebook = plugin.parameterize_notebook(
            notebook_id=notebook_id, parameters=parameters, notebook=notebook
        )
        log.info(f"Parameterized notebook")
        event_store = NotebookEventStore(notebook=notebook)
        event_store.save_event(
            NotebookExecutionCreated(
                plugin_name=plugin_name, notebook_id=notebook_id, parameters=parameters,
            )
        )

        if parameterize_only:
            return event_store.notebook

        # execute notebook
        executor = plugin.get_notebook_executor()
        # TODO: remove start time and end time here if its never used
        start_time = datetime.utcnow()
        exception = await executor.execute_notebook_async(notebook=event_store.notebook)
        end_time = datetime.utcnow()
        log.info(
            f"Executor executed notebook. start_time={start_time.isoformat()}, end_time={end_time.isoformat()}"
        )
        output_json_str: Optional[str] = None
        output_validation = SchemaValidationResponse(is_valid=True)
        # check if notebook has output
        output_result = plugin.get_nbschema().get_notebook_output(
            notebook=event_store.notebook
        )
        if output_result.present:
            # get notebook output
            output_json_str = output_result.json_str
            # perform output validation
            notebook_config = plugin.get_resolver().resolve_config(
                notebook_id=notebook_id
            )
            output_validation = plugin.get_nbschema().validate_output(
                output=json.loads(output_json_str), notebook_config=notebook_config
            )
        # save execution event
        event_store.save_event(
            NotebookExecuted(
                start_time=start_time,
                end_time=end_time,
                exception=exception,
                output_validation=output_validation,
                output_json_str=output_json_str,
            )
        )
        return event_store.notebook
