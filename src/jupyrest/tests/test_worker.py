import pytest
from tests.conftest import Notebooks
from jupyrest.workers.base import Worker
from jupyrest.errors import (
    BaseError,
    PluginNotFound,
    NotebookNotFound,
    InputSchemaValidationError,
)
from jupyrest.domain import (
    NotebookEventStore,
    NotebookExecutionCreated,
    NotebookExecuted,
)
from jupyrest.plugin import PluginManager


@pytest.mark.asyncio
async def test_worker_plugin_not_found(worker: Worker):
    notebook_id = Notebooks.io_contract_example
    parameters = {}
    plugin_name = "does not exist"
    result = await worker.execute_notebook_async(
        plugin_name=plugin_name, notebook_id=notebook_id, parameters=parameters
    )
    assert isinstance(result, PluginNotFound)
    assert result.plugin_name == plugin_name


@pytest.mark.asyncio
async def test_worker_notebook_not_found(worker: Worker):
    notebook_id = "does_not_exist"
    parameters = {}
    plugin_name = PluginManager.DEFAULT_PLUGIN_NAME
    result = await worker.execute_notebook_async(
        plugin_name=plugin_name, notebook_id=notebook_id, parameters=parameters
    )
    assert isinstance(result, NotebookNotFound)
    assert result.notebook_id == notebook_id


@pytest.mark.asyncio
async def test_worker_invalid_input_schema(worker: Worker):
    notebook_id = Notebooks.io_contract_example
    parameters = {}
    plugin_name = PluginManager.DEFAULT_PLUGIN_NAME
    result = await worker.execute_notebook_async(
        plugin_name=plugin_name, notebook_id=notebook_id, parameters=parameters
    )
    assert isinstance(result, InputSchemaValidationError)


@pytest.mark.asyncio
async def test_parameterize_only(worker: Worker):
    notebook_id = Notebooks.io_contract_example
    parameters = {"foo": "foo", "bar": 500, "baz": "baz"}
    response = await worker.execute_notebook_async(
        plugin_name=PluginManager.DEFAULT_PLUGIN_NAME,
        notebook_id=notebook_id,
        parameters=parameters,
        parameterize_only=True,
    )
    assert not isinstance(response, BaseError)
    event_store = NotebookEventStore(notebook=response)
    # assert that the execution was created, but not executed
    execution_created = event_store.get_event(NotebookExecutionCreated)
    assert execution_created is not None
    assert isinstance(execution_created, NotebookExecutionCreated)

    notebook_executed = event_store.get_event(NotebookExecuted)
    assert notebook_executed is None

    # assert execution details are retained
    assert execution_created.notebook_id == notebook_id
    assert execution_created.parameters == parameters
    assert execution_created.plugin_name == PluginManager.DEFAULT_PLUGIN_NAME
